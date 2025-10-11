from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class AccountMove(models.Model):
    _inherit = 'account.move'

    fixed_rebate_move_id = fields.Many2one('account.move', copy=False, string='Rebate Created From', readonly=1)
    fixed_rebate_lines = fields.One2many('account.move', 'fixed_rebate_move_id', string="Fixed Rebate Entries")
    fixed_rebate_line_ids = fields.One2many('account.move.line', 'rebate_entry_of', string="Fixed Rebate Entries Lines")
    rebate_type = fields.Selection([('fixed', 'Fixed'), ('progressive', 'Progressive')], string="Rebate Type",
                                   copy=False)
    rebate_master_id = fields.Many2one('rebate.master', string='Rebate')
    reverse_status = fields.Boolean(default=False)
    enty_type = fields.Selection([('normal', 'Normal'), ('reverse', 'Reverse')], string="Entry Type")
    rebate_applied = fields.Float()
    sale_amount = fields.Float()

    # fields for tax_invoice
    delivery_date = fields.Date()
    actual_delivery_date = fields.Date()
    driver = fields.Many2one('res.users')
    carrier = fields.Many2one('res.users')
    carrier_id = fields.Many2one('user.vehicle')
    # fields for wms
    delivery_status = fields.Selection([('not_delivered', 'Not Delivered'), ('delivered', 'Delivered')],
                                       default='not_delivered')
    rebate_item_id = fields.Many2one('rebate.item', string='Rebate Item')

    is_rebate_recomputed = fields.Boolean("Is rebate recomputed by scheduler")

    def action_delivery(self):
        self.delivery_status = 'delivered'


    def run_rebate_recomputation(self):
        credit_notes = self.search([('move_type', '=', 'out_refund'),
                                    ('is_rebate_recomputed', '=', False),
                                    ('partner_id.customer_sub_classification', 'not in', ['Van Sales', 'Traditional - B Class', 'E-Commerce']),
                                    ('invoice_origin', 'ilike', 'SR/2023/'),
                                    ('state', '=', 'posted')])
        total = len(credit_notes)
        count = 0
        for crd_note in credit_notes:
            count = count + 1
            crd_note.check_and_post_rebate_as_required()

    def check_and_post_rebate_as_required(self):
        for inv in self:
            rebates = self.search([('fixed_rebate_move_id', 'in', self.ids), ('state', '!=', 'cancel')])
            if not rebates:
                inv.update_rebates()
                inv.is_rebate_recomputed = True


    def check_and_post_rebate_rpc(self, invoice_ids):


        rebate_date_mapping = {}

        #RAK National Markets Rebate 2023
        rebate_date_mapping[86] = fields.date(2023, 1, 1)

        #Urban Foods Rebate 2023
        rebate_date_mapping[90] = fields.date(2023, 4, 1)

        # New Westzone Rebate 2023
        rebate_date_mapping[85] = fields.date(2023, 3, 1)

        # Union Coop Rebate 2023
        rebate_date_mapping[89] = fields.date(2023, 5, 1)

        # Union Coop Rebate 2023 (Dec Sales Event)
        rebate_date_mapping[94] = fields.date(2023, 5, 1)

        # Union Coop Rebate 2023 (BTS Event)
        rebate_date_mapping[95] = fields.date(2023, 5, 1)

        # Al Ain Coop Rebate 2023
        rebate_date_mapping[66] = fields.date(2023, 4, 1)

        # Gala Rebate 2023
        rebate_date_mapping[77] = fields.date(2023, 4, 1)

        # Sharjah Coop Rebate 2022 : 2023
        rebate_date_mapping[36] = fields.date(2023, 1, 1)

        total = len(invoice_ids)
        count = 0

        invoices = self.browse(invoice_ids)
        rebate_recomputed = []
        for inv in invoices:
            count = count + 1
            print("\n\ninv ==>> ", count, " :: ", total)
            invoice_date = False
            for rebate in inv.partner_id.property_product_pricelist.rebate_ids:
                if rebate.id in rebate_date_mapping:
                    invoice_date = rebate_date_mapping[rebate.id]
                    break
            if invoice_date and inv.invoice_date >= invoice_date:
                print("Updating REB")
                #unlink rebates move
                inv._cancel_fixed_rebate_moves()

                #repost rebate
                inv.update_rebates()
                inv.is_rebate_recomputed = True
                rebate_recomputed.append(inv.id)

        return rebate_recomputed


    def crd_notes_repost_rebate_rpc(self, invoice_ids):


        rebate_date_mapping = {}

        #RAK National Markets Rebate 2023
        rebate_date_mapping[86] = fields.date(2023, 1, 1)

        #Urban Foods Rebate 2023
        rebate_date_mapping[90] = fields.date(2023, 4, 1)

        # New Westzone Rebate 2023
        rebate_date_mapping[85] = fields.date(2023, 3, 1)

        # Union Coop Rebate 2023
        rebate_date_mapping[89] = fields.date(2023, 5, 1)

        # Union Coop Rebate 2023 (Dec Sales Event)
        rebate_date_mapping[94] = fields.date(2023, 5, 1)

        # Union Coop Rebate 2023 (BTS Event)
        rebate_date_mapping[95] = fields.date(2023, 5, 1)

        # Al Ain Coop Rebate 2023
        rebate_date_mapping[66] = fields.date(2023, 4, 1)

        # Gala Rebate 2023
        rebate_date_mapping[77] = fields.date(2023, 4, 1)

        # Sharjah Coop Rebate 2022 : 2023
        rebate_date_mapping[36] = fields.date(2023, 1, 1)

        total = len(invoice_ids)
        count = 0

        invoices = self.browse(invoice_ids)
        rebate_recomputed = []
        for inv in invoices:
            count = count + 1
            invoice_date = False
            for rebate in inv.partner_id.property_product_pricelist.rebate_ids:
                if rebate.id in rebate_date_mapping:
                    invoice_date = rebate_date_mapping[rebate.id]
                    break
            if invoice_date and inv.invoice_date >= invoice_date:
                print("Updating REB")
                #unlink rebates move
                inv._cancel_fixed_rebate_moves()

                #repost rebate
                inv.update_rebates()
                inv.is_rebate_recomputed = True
                rebate_recomputed.append(inv.id)

        return rebate_recomputed


    def update_rebates(self):
        self._create_fixed_rebate_moves()
        # CHA Uncomment below testing speed
        #self._unlink_existing_rebate_items()
        #self.invoice_line_ids._create_rebate_item()
        #self._update_rebate_entries()

    def _unlink_existing_rebate_items(self, domain=None):
        """unlink rebate items with same invoice_id (if any)"""
        if not domain:
            domain = []
        domain += [('invoice_line_id', 'in', self.mapped('invoice_line_ids').ids)]
        self.env['rebate.item']._remove_existing_items(domain)

    def action_post(self):
        res = super(AccountMove, self).action_post()
        #CHA Uncomment below testing speed
        for invoice in self.sorted('date'):
            invoice.update_rebates()

        return res

    def button_draft(self):
        # unlink all related rebate items to avoid duplicate records. Then updates related rebate entries.
        res = super(AccountMove, self).button_draft()
        # CHA Uncomment below testing speed
        #self._unlink_existing_rebate_items()
        #self._update_rebate_entries()
        # cancel all fixed rebate moves created from this move
        self._cancel_fixed_rebate_moves()
        return res

    # def button_cancel(self):
    #     # cancel all fixed rebate moves created from this move
    #     res = super(AccountMove, self).button_cancel()
    #     self._cancel_fixed_rebate_moves()
    #     return res

    def _update_rebate_entries(self):
        pricelists = self.mapped('invoice_line_ids.sale_line_ids.order_id.pricelist_id')
        RebateEntry = self.env['rebate.entry']
        # if self.partner_id.parent_id
        for invoice in self:
            rebate_ids = pricelists.mapped('rebate_ids')
            rebates = rebate_ids.filtered(lambda l: l.date_start <= invoice.date <= l.date_end)
            for rebate in rebates:
                RebateEntry._update_rebate(partner_id=invoice.partner_id, rebate_id=rebate)
        return True

    def _cancel_fixed_rebate_moves(self):
        moves = self.search([('fixed_rebate_move_id', 'in', self.ids), ('state', '!=', 'cancel')])
        moves.button_cancel()
        return True

    def _create_fixed_rebate_moves(self):
        journal_id = self.env['ir.config_parameter'].sudo().get_param('kg_sarya_rebate.rebate_journal_id', False)
        print("1>>>>>>>>>>>>>>>>>>>>>>>>>>")
        if self.move_type in ('out_invoice', 'out_refund'):
            if not journal_id:
                raise UserError(_("You must configure journal for rebate in settings"))
        journal_id = int(journal_id)
        move_ids = self.browse()
        if self.move_type in ('out_invoice', 'out_refund'):
            partner_id = self.env['rebate.entry']._get_rebate_partner(self.partner_id.id)
            partner = partner_id.id
            sale_id = self.sale_order_id
            if not sale_id:
                sales = self.invoice_line_ids.mapped('sale_line_ids.order_id')
                sale_id = sales[0] if sales else sale_id
            rebate_ids = sale_id.pricelist_id.rebate_ids or partner_id.property_product_pricelist.rebate_ids
            for rebate in rebate_ids:
                if self.invoice_date >= rebate.date_start  and self.invoice_date <= rebate.date_end:
                    move_line_vals = []
                    invoice_amount = 0.0
                    for line in self.invoice_line_ids:
                        if line.product_id:
                            if rebate.product_type == 'selected':
                                if line.product_id.section.id not in rebate.customer_section_ids.ids:
                                    continue
                                if line.product_id.brand.id not in rebate.brand_id.ids:
                                    continue
                            if rebate.is_rebate_computed_on_untaxed:
                                invoice_amount += line.price_subtotal
                            else:
                                invoice_amount += line.price_total
                    for item in rebate.fixed_ids:
                        if item.rebate_active:
                            rebate_amount = (item.percentage * invoice_amount) / 100
                            narration = '%s: %s' % (rebate.name, item.description)
                            if float_compare(rebate_amount, 0.0,
                                             precision_rounding=self.currency_id.rounding) != 0:
                                if self.move_type == 'out_invoice':
                                    # for normal invoice
                                    move_line_vals.append((0, 0, {
                                        'name': narration,
                                        'account_id': item.account_id.id,
                                        'debit': rebate_amount,
                                        'partner_id': partner,
                                        'rebate_fixed_id' : item.id,
                                        'rebate_entry_of' : self.id,
                                        'date_maturity' : self.invoice_date_due
                                    }))
                                    move_line_vals.append((0, 0, {
                                        'name': narration,
                                        'account_id': partner_id.property_account_receivable_id.id,
                                        'credit': rebate_amount,
                                        'partner_id': partner,
                                        'rebate_fixed_id': item.id,
                                        'rebate_entry_of': self.id,
                                        'date_maturity': self.invoice_date_due
                                    }))
                                else:
                                    # for invoice credit note
                                    move_line_vals.append((0, 0, {
                                        'name': narration,
                                        'account_id': item.account_id.id,
                                        'credit': rebate_amount,
                                        'partner_id': partner,
                                        'rebate_fixed_id': item.id,
                                        'rebate_entry_of': self.id,
                                        'date_maturity': self.invoice_date_due
                                    }))
                                    move_line_vals.append((0, 0, {
                                        'name': narration,
                                        'account_id': partner_id.property_account_receivable_id.id,
                                        'debit': rebate_amount,
                                        'partner_id': partner,
                                        'rebate_fixed_id': item.id,
                                        'rebate_entry_of': self.id,
                                        'date_maturity': self.invoice_date_due
                                    }))
                    for charges in rebate.other_ids.filtered(
                            lambda l: sale_id and sale_id.partner_id.id in l.partner_id.ids and l.account_id):
                        if charges.rebate_active:
                            rebate_amount = (charges.percentage * invoice_amount) / 100
                            narration = '%s: %s' % (rebate.name, charges.description)
                            if float_compare(rebate_amount, 0.0,
                                             precision_rounding=self.currency_id.rounding) != 0:
                                if self.move_type == 'out_invoice':
                                    # for normal invoice
                                    move_line_vals.append((0, 0, {
                                        'name': narration,
                                        'account_id': charges.account_id.id,
                                        'debit': rebate_amount,
                                        'partner_id': partner,
                                        'rebate_other_id' : charges.id,
                                        'rebate_entry_of': self.id,
                                        'date_maturity': self.invoice_date_due
                                    }))
                                    move_line_vals.append((0, 0, {
                                        'name': narration,
                                        'account_id': partner_id.property_account_receivable_id.id,
                                        'credit': rebate_amount,
                                        'partner_id': partner,
                                        'rebate_other_id': charges.id,
                                        'rebate_entry_of': self.id,
                                        'date_maturity': self.invoice_date_due
                                    }))
                                else:
                                    # for invoice credit note
                                    move_line_vals.append((0, 0, {
                                        'name': narration,
                                        'account_id': charges.account_id.id,
                                        'credit': rebate_amount,
                                        'partner_id': partner,
                                        'rebate_other_id': charges.id,
                                        'rebate_entry_of': self.id,
                                        'date_maturity': self.invoice_date_due
                                    }))
                                    move_line_vals.append((0, 0, {
                                        'name': narration,
                                        'account_id': partner_id.property_account_receivable_id.id,
                                        'debit': rebate_amount,
                                        'partner_id': partner,
                                        'rebate_other_id': charges.id,
                                        'rebate_entry_of': self.id,
                                        'date_maturity': self.invoice_date_due
                                    }))
                    if move_line_vals:
                        move_vals = {
                            'ref': '%s - %s' % (rebate.name, self.name),
                            'move_type': 'entry',
                            'journal_id': journal_id,
                            'date': self.invoice_date or fields.Date.context_today(self),
                            'line_ids': move_line_vals,
                            'rebate_type': 'fixed',
                            'rebate_master_id': rebate.id,
                            'sale_order_id': sale_id.id,
                            'sale_order_customer_id': sale_id.partner_id.id or self.partner_id.id,
                            'fixed_rebate_move_id': self.id,
                            'invoice_date_due': self.invoice_date_due
                        }
                        move_id = self.create(move_vals)
                        move_id.action_post()
                        move_ids |= move_id
        return move_ids


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    rebate_entry_id = fields.Many2one('rebate.entry', string='Rebate Entry', ondelete='set null')
    rebate_type = fields.Selection(related='move_id.rebate_type', store=True)
    rebate_fixed_id = fields.Many2one('rebate.fixed.item', string='Rebate Fixed', ondelete='set null')
    rebate_other_id = fields.Many2one('rebate.other.item', string='Rebate Other', ondelete='set null')
    rebate_entry_of = fields.Many2one('account.move', string='Rebate Entry Of', ondelete='set null')

    def _create_rebate_item(self):
        RebateItem = self.env['rebate.item']
        for ml in self:
            RebateItem._update_rebate_items(ml)

    def _prepare_fixed_rebate_items(self, rebate_id):
        """Returns values to create rebate.fixed.item.line from the given rebate_id"""

        vals = []
        for line in rebate_id.fixed_ids:
            amount = (line.percentage * self.price_total) / 100
            vals.append((0, 0, {
                'fixed_rebate_id': line.id,
                'rebate_fixed_amount': amount,
            }))
        return vals
