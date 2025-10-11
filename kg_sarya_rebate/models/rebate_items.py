# -*- coding: utf-8 -*-

from odoo import models, fields, _, api
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


class RebateItem(models.Model):
    _name = "rebate.item"
    _description = "Rebate Items"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))
    date = fields.Date('Date', default=fields.Date.today, copy=False, readonly=1)
    rebate_entry_id = fields.Many2one('rebate.entry', 'Rebate Entry', ondelete='set null')
    amount = fields.Monetary(string='Invoice Amount(Com. Currency)', currency_field='company_currency_id',
                             help='Untaxed amount of the invoice converted to company currency', copy=False)
    sale_line_id = fields.Many2one('sale.order.line', 'Sale Line', readonly=True)
    sale_id = fields.Many2one(related='sale_line_id.order_id', string='Sale Order', store=True)
    invoice_line_id = fields.Many2one('account.move.line', 'Invoice Line', index=True, required=True, readonly=True)
    invoice_id = fields.Many2one(related='invoice_line_id.move_id', string='Invoice', store=True)
    product_id = fields.Many2one(related='invoice_line_id.product_id', store=True)
    invoice_line_amount = fields.Monetary(related='invoice_line_id.price_total', store=True,
                                          currency_field='currency_id',
                                          string='Invoice Amount', help='Untaxed amount of the invoice')
    invoice_date = fields.Date(related='invoice_line_id.date', string='Invoice Date', store=True)
    invoice_move_type = fields.Selection(related='invoice_line_id.move_id.move_type', string='Invoice Type', store=True)
    product_packaging_id = fields.Many2one(related='invoice_line_id.package_id', store=True)
    product_packaging_qty = fields.Float(related='invoice_line_id.product_packaging_qty', store=True,
                                         string='Pkg Qty')
    partner_id = fields.Many2one(related='invoice_line_id.partner_id', store=True)
    brand_id = fields.Many2one(related='invoice_line_id.product_id.brand', store=True)
    section_id = fields.Many2one(related='invoice_line_id.product_id.section', store=True)
    user_id = fields.Many2one(related='invoice_line_id.move_id.user_id', store=True)
    # rebates
    rebate_id = fields.Many2one('rebate.master', string='Rebate')
    fixed_rebate_lines = fields.One2many('rebate.fixed.item.line', 'parent_id', 'Fixed Rebates')
    fixed_rebate_amount = fields.Monetary('Fixed Rebate Amount', currency_field='company_currency_id')
    fixed_rebate_percentage = fields.Float(string='Fixed Rebate %')
    progressive_rebate_id = fields.Many2one('rebate.progressive.item', 'Prog. Rebate')
    progressive_rebate_percentage = fields.Float(string='Prog. Rebate %', copy=False)
    progressive_rebate_amount = fields.Monetary('Prog. Rebate Amount', currency_field='company_currency_id')
    total_rebate_amount = fields.Monetary('Total Rebate Amount', compute='_compute_total_rebate_amount',
                                          currency_field='company_currency_id', store=True)

    company_id = fields.Many2one(related='invoice_line_id.company_id', store=True)
    currency_id = fields.Many2one(related='invoice_line_id.currency_id', store=True)
    company_currency_id = fields.Many2one(related='invoice_line_id.company_currency_id', store=True)
    item_type = fields.Selection(
        string='Type',
        selection=[('normal', 'Normal'),
                   ('reservation', 'Reservation')],
        required=True, copy=False)

    active = fields.Boolean('Active', default=True,
                            help="By unchecking the active field, you may "
                                 "exclude this rebate item from the rebate calculations.")

    invoice_state = fields.Selection(related='invoice_line_id.parent_state', string='Invoice State', store=True,
                                     readonly=True)

    @api.depends('fixed_rebate_amount', 'progressive_rebate_amount')
    def _compute_total_rebate_amount(self):
        for rec in self:
            rec.total_rebate_amount = rec.fixed_rebate_amount + rec.progressive_rebate_amount

    @api.model
    def create(self, vals):
        if 'company_id' in vals:
            self = self.with_company(vals['company_id'])
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            if 'date' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date']))
            vals['name'] = self.env['ir.sequence'].next_by_code('rebate.entry', sequence_date=seq_date) or _('New')
        result = super(RebateItem, self).create(vals)
        return result

    def unlink(self):
        partner_rebates = []
        Partner = self.env['res.partner']
        Rebate = self.env['rebate.master']
        # we store partner and rebate before unlinking self as it won't be available after super()
        for rec in self:
            partner_rebates.append({
                'partner_id': rec.partner_id.id,
                'rebate_id': rec.rebate_id.id,
            })
        res = super(RebateItem, self).unlink()
        RebateEntry = self.env['rebate.entry']
        for item in partner_rebates:
            partner = Partner.browse(item['partner_id'])
            rebate = Rebate.browse(item['rebate_id'])
            RebateEntry._update_rebate(partner, rebate)
        return res

    def copy(self, default=None):
        # restrict user to duplicate a rebate items as the records have to be created functionally.
        raise UserError(_('Duplicating a rebate item is not allowed.'))

    def action_show_fixed_rebates(self):
        self.ensure_one()
        action = self.env.ref("kg_sarya_rebate.action_rebate_fixed_item").sudo().read()[0]
        action["res_id"] = self.id
        return action

    def action_view_account_moves(self):
        action = self.env.ref("account.action_move_journal_line").sudo().read()[0]
        moves = self.move_ids
        if len(moves) > 1:
            action["domain"] = [("id", "in", moves.ids)]
        elif moves:
            action["views"] = [(self.env.ref("account.view_move_form").id, "form")]
            action["res_id"] = moves.id
        return action

    def _get_rebate_partner(self, partner_id):
        """We consider only parent customer to apply rebates"""
        partner_id = self.env['res.partner'].sudo().browse(partner_id)
        if partner_id.is_parent:
            return partner_id
        partner = partner_id.parent_id.id
        while partner:
            partner = partner.parent_id.id
        if not partner:
            partner = partner_id
        return self.env['res.partner'].sudo().browse(partner.id)

    def _remove_existing_items(self, domain):
        # remove rebate items that match the given domain
        items = self.search(domain)
        items.unlink()
        return True

    def _update_existing_items(self, partner_id, progressive_slab):
        domain = [('progressive_rebate_id', '!=', progressive_slab.id)]
        items = self._gather(partner_id, progressive_slab.rebate_id, domain=domain)
        for item in items:
            slab_amount = (progressive_slab.rebate_percentage * item.amount) / 100
            fixed_amount = (progressive_slab.rebate_id.total_without_progressive * item.amount) / 100
            item.write({
                'progressive_rebate_percentage': progressive_slab.rebate_percentage,
                'progressive_rebate_id': progressive_slab.id,
                'progressive_rebate_amount': slab_amount,
                # we change fixed rebate value as well to make sure rebate calculation is up-to-date
                'fixed_rebate_amount': fixed_amount,
            })

    def _update_rebate_items(self, invoice_line):
        move_id = invoice_line.move_id
        invoice_partner = self._get_rebate_partner(move_id.partner_id.id)
        if invoice_line.sale_line_ids and move_id.move_type in ('out_invoice', 'out_refund'):
            if invoice_line.sale_line_ids:
                sale_line_id = invoice_line.sale_line_ids[0]
                pricelist = sale_line_id.order_id.pricelist_id
            else:
                sale_line_id = False
                pricelist = invoice_partner.property_product_pricelist
            if any(item in pricelist.customer_ids.ids for item in [invoice_partner.id, move_id.partner_id.id]):
                product = invoice_line.product_id
                price_total = invoice_line.price_total
                # convert to company currency if needed
                if invoice_line.currency_id and invoice_line.currency_id.id != invoice_line.company_currency_id.id:
                    price_total = invoice_line.currency_id._convert(price_total, invoice_line.company_currency_id,
                                                                    invoice_line.company_id,
                                                                    invoice_line.date,
                                                                    round=invoice_line.company_currency_id.rounding)
                invoice_date = move_id.invoice_date
                rebate_ids = pricelist.rebate_ids.filtered(
                    lambda l: l.date_start <= invoice_date <= l.date_end)
                for rebate in rebate_ids:
                    if rebate.product_type == 'selected':
                        if product.section.id not in rebate.customer_section_ids.ids \
                                and product.brand.id not in rebate.brand_id.ids:
                            pass
                    sign = -1 if move_id.move_type == 'out_refund' else 1
                    fixed_rebate_amount = (rebate.total_without_progressive * price_total) / 100

                    # check progressive slab
                    previous_rebate_item_amount = self._get_total_rebated_amount(invoice_partner, rebate)
                    total_invoice_amount = previous_rebate_item_amount + price_total
                    progressive_slab, item_type = invoice_partner._get_progressive_rebate_slab(rebate,
                                                                                               total_invoice_amount)
                    self._update_existing_items(invoice_partner, progressive_slab)
                    progressive_amount = (progressive_slab.rebate_percentage * price_total) / 100
                    fixed_lines = invoice_line._prepare_fixed_rebate_items(rebate)
                    if not float_is_zero(fixed_rebate_amount + progressive_amount,
                                         precision_rounding=invoice_line.product_uom_id.rounding):
                        entry_id = self.env['rebate.entry']._get_customer_current_rebate(invoice_partner, rebate)
                        if not entry_id:
                            # create an empty rebate entry to link with.
                            entry_vals = {
                                'rebate_id': rebate.id,
                                'partner_id': invoice_partner.id,
                            }
                            entry_id |= entry_id._create_dummy_entry(entry_vals)
                        values = {
                            'sale_line_id': sale_line_id.id,
                            'invoice_line_id': invoice_line.id,
                            'rebate_id': rebate.id,
                            'amount': price_total,
                            'progressive_rebate_percentage': progressive_slab.rebate_percentage or 0.0,
                            'fixed_rebate_percentage': rebate.total_without_progressive,
                            'fixed_rebate_amount': sign * fixed_rebate_amount or 0.0,
                            'progressive_rebate_amount': sign * progressive_amount or 0.0,
                            'progressive_rebate_id': progressive_slab and progressive_slab.id or False,
                            'fixed_rebate_lines': fixed_lines,
                            'item_type': item_type,
                            'rebate_entry_id': entry_id.id,
                        }
                        # unlink rebate item with sale invoice line if any
                        rebate_item = self._gather(invoice_partner, rebate,
                                                   domain=[('invoice_line_id', '=', invoice_line.id)])
                        rebate_item.unlink()
                        self.create(values)

    def _gather(self, partner_id, rebate_id, reverse=False, date_from=None, date_to=None, domain=None):
        if not date_from:
            date_from = rebate_id.date_start
        if not date_to:
            date_to = rebate_id.date_end
        if not domain:
            domain = []
        domain += [('partner_id', '=', partner_id.id), ('rebate_id', '=', rebate_id.id)]
        if date_from:
            domain += [('invoice_date', '>=', date_from)]
        if date_to:
            domain += [('invoice_date', '<=', date_to)]
        return self.search(domain, order='invoice_date' if reverse else 'invoice_date desc')

    def _get_total_rebated_amount(self, partner_id, rebate_id):
        items = self._gather(partner_id, rebate_id)
        amount = sum(items.mapped('amount'))
        return amount


class RebateFixedItemLine(models.Model):
    _name = "rebate.fixed.item.line"
    _description = "Fixed Rebate Breakdown"
    _rec_name = 'fixed_rebate_id'

    parent_id = fields.Many2one('rebate.item', 'Rebate Item', ondelete='cascade')
    fixed_rebate_id = fields.Many2one('rebate.fixed.item', 'Fixed Rebate Item')
    rebate_fixed_amount = fields.Monetary('Amount')

    # related fields of fixed_rebate_id
    currency_id = fields.Many2one(related='parent_id.currency_id')
    rebate_id = fields.Many2one(related='fixed_rebate_id.rebate_id')
    account_id = fields.Many2one(related='fixed_rebate_id.account_id')
    percentage = fields.Float(related='fixed_rebate_id.percentage')
