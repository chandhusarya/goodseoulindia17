from collections import defaultdict
from datetime import date

from dateutil.relativedelta import relativedelta
from odoo import http
from odoo import models, fields, api, _
from odoo.exceptions import AccessError, ValidationError, MissingError, UserError
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.tools import float_is_zero, html_keep_url, is_html_empty
from pytz import timezone, UTC


class SaleOrderInherit(models.Model):
    _inherit = "sale.order"

    # multi_pricelist = fields.Many2many('product.pricelist', string="Multi PriceList")
    sales_category = fields.Many2one('sales.category', string="Sale Category", ondelete='cascade')
    disc_margin = fields.Monetary("Margin")
    disc_margin_percent = fields.Float("Margin (%)")
    amount_line_total = fields.Monetary("Margin", compute='_compute_line_total', store=True)
    trade_channel = fields.Many2one('trade.channel')
    lpo_attach_id = fields.Many2many('ir.attachment', 'lpo_attach_rel', 'doc_id88', 'attach_id99', string="Attachment",
                                     copy=False)
    picking_type_id = fields.Many2one('stock.picking.type')
    is_vansales_order = fields.Boolean("Is vansales Order")
    journal_id = fields.Many2one('account.journal', domain=[('type', '=', 'sale')])

    @api.model
    def create(self, vals):
        res = super(SaleOrderInherit, self).create(vals)
        # fix attachment ownership
        for template in res:
            if template.lpo_attach_id:
                template.lpo_attach_id.sudo().write({'res_model': self._name, 'res_id': template.id})
        return res

    @api.onchange('partner_id')
    def onchange_partner_dtls_id(self):
        if self.partner_id:
            self.partner_id.property_product_pricelist = False
            self.trade_channel = self.partner_id.trade_channel.id
            res = {}
            price_list = self.env['product.pricelist'].search([('customer_ids', '=', self.partner_id.id)])
            price_list_domain = []
            for plist in price_list:
                if plist.end_date:
                    if plist.end_date > date.today():
                        price_list_domain.append(plist.id)
                else:
                    price_list_domain.append(plist.id)
            res['domain'] = {'pricelist_id': [('id', '=', price_list_domain)]}

            picking_type_id = False
            if self.partner_id.customer_sub_classification.picking_type_id:
                picking_type_id = self.partner_id.customer_sub_classification.picking_type_id.id

            if self.partner_id.customer_sub_classification3 and\
                    self.partner_id.customer_sub_classification3.picking_type_id:
                picking_type_id = self.partner_id.customer_sub_classification3.picking_type_id.id

            self.picking_type_id = picking_type_id

            return res

    @api.onchange('picking_type_id')
    def onchange_picking_type_id(self):
        if self.picking_type_id:
            self.warehouse_id = self.picking_type_id.warehouse_id and self.picking_type_id.warehouse_id.id

    @api.onchange('partner_id')
    def onchange_partner_prlst(self):
        if self.partner_id:
            self.payment_term_id = self.partner_id.property_payment_term_id.id
            price_list = self.env['product.pricelist'].search([('customer_ids', '=', self.partner_id.id), ('special', '=', False)],
                                                              order="create_date asc")
            for price in price_list:
                if price.end_date:
                    if price.end_date > date.today():
                        self.pricelist_id = price.id
                else:
                    self.pricelist_id = price.id

    # self.payment_term_id = 2

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """
        Update the following fields when the partner is changed:
        - Pricelist
        - Payment terms
        - Invoice address
        - Delivery address
        - Sales Team
        """
        if not self.partner_id:
            self.update({
                'partner_invoice_id': False,
                'partner_shipping_id': False,
                'fiscal_position_id': False,
            })
            return

        self = self.with_company(self.company_id)

        addr = self.partner_id.address_get(['delivery', 'invoice'])
        if self.partner_id.is_parent == False:
            parent_addr = self.partner_id.parent_customer_id.address_get(['delivery', 'invoice'])
            values = {
                'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False,
                'payment_term_id': self.partner_id.property_payment_term_id and self.partner_id.property_payment_term_id.id or False,
                'partner_invoice_id': parent_addr['invoice'],
                'partner_shipping_id': addr['delivery'],
            }
        else:
            values = {
                'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False,
                'payment_term_id': self.partner_id.property_payment_term_id and self.partner_id.property_payment_term_id.id or False,
                'partner_invoice_id': addr['invoice'],
                'partner_shipping_id': addr['delivery'],
            }
        partner_user = self.partner_id.user_id or self.partner_id.commercial_partner_id.user_id
        user_id = partner_user.id
        if not self.env.context.get('not_self_saleperson'):
            user_id = user_id or self.env.context.get('default_user_id', self.env.uid)
        if user_id and self.user_id.id != user_id:
            values['user_id'] = user_id

        if self.env['ir.config_parameter'].sudo().get_param('account.use_invoice_terms'):
            if self.terms_type == 'html' and self.env.company.invoice_terms_html:
                baseurl = html_keep_url(self.get_base_url() + '/terms')
                values['note'] = _('Terms & Conditions: %s', baseurl)
            elif not is_html_empty(self.env.company.invoice_terms):
                values['note'] = self.with_context(lang=self.partner_id.lang).env.company.invoice_terms
        if not self.env.context.get('not_self_saleperson') or not self.team_id:
            values['team_id'] = self.env['crm.team'].with_context(
                default_team_id=self.partner_id.team_id.id
            )._get_default_team_id(domain=['|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)],
                                   user_id=user_id)
        self.update(values)

    @api.constrains('lpo_attach_id', 'state')
    def check_ir_attachment(self):
        for rec in self:
            if not rec.is_vansales_order:
                if rec.picking_type_id and 'Event' not in rec.picking_type_id.name:
                    if len(rec.lpo_attach_id.ids) < 1 and rec.state not in ['draft']:
                        raise ValidationError("Please upload LPO document")

    @api.constrains('client_order_ref')
    def constrains_client_order_ref(self):
        if self.client_order_ref:
            sale_order = self.env['sale.order'].search(
                [('partner_id', '=', self.partner_id.id), ('client_order_ref', '=', self.client_order_ref),
                 ('state', 'not in', ['cancel'])])
            if len(sale_order) > 1:
                raise ValidationError('This customer reference already exists for another sale order')

    @api.onchange('client_order_ref')
    def _onchange_client_order_ref(self):
        if self.client_order_ref:
            sale_order = self.env['sale.order'].search(
                [('partner_id', '=', self.partner_id.id), ('client_order_ref', '=', self.client_order_ref),
                 ('state', 'not in', ['cancel'])])
            if len(sale_order) > 1:
                raise ValidationError('This customer reference already exists for another sale order')

    # margin calculation
    @api.depends('order_line.price_total')
    def _compute_line_total(self):
        amount_line_total = 0.0
        for line in self.order_line:
            amount_line_total += (line.product_uom_qty * line.price_unit)
        self.amount_line_total = amount_line_total

    # override--to include journal of sale category
    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()

        if not self.partner_id.trade_channel and self.env.company.company_type == 'distribution':
            raise UserError(_('Please define an Trade Channel for the customer'))

        if self.partner_id.trade_channel or self.journal_id:
            journal = self.journal_id or False
            if not journal:
                journal = self.partner_id.trade_channel.journal
            if not journal:
                raise UserError(_('Please define an accounting sales journal for the customer'))
        invoice_vals = {
            'ref': self.client_order_ref or '',
            'move_type': 'out_invoice',
            'narration': self.note,
            'currency_id': self.pricelist_id.currency_id.id,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'source_id': self.source_id.id,
            'user_id': self.user_id.id,
            'invoice_user_id': self.user_id.id,
            'team_id': self.team_id.id,
            'partner_id': self.partner_invoice_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id._get_fiscal_position(
                self.partner_invoice_id)).id,
            'partner_bank_id': self.company_id.partner_id.bank_ids[:1].id,
            'journal_id': journal.id,  # company comes from the journal
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'payment_reference': self.reference,
            'transaction_ids': [(6, 0, self.transaction_ids.ids)],
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
            'invoice_date': self.commitment_date,
            'delivery_date': self.commitment_date,
            'sale_order_id': self.id,
            'sale_order_customer_id': self.partner_id.id,
        }
        return invoice_vals



    @api.onchange('partner_id')
    def set_sale_person(self):
        if self.partner_id:
            self.user_id = self.partner_id.account_manager_id.id


class SaleOrderLineInherit(models.Model):
    _inherit = "sale.order.line"

    qty_status = fields.Boolean(default=False)
    disc_margin = fields.Float(
        "Margin")
    disc_margin_percent = fields.Float(
        "Margin (%)")
    actaul_price = fields.Float(compute='_compute_total_amount', store=True)
    pricelist_item_id = fields.Many2one('product.pricelist.item')

    @api.onchange('product_id')
    def _set_pkg_qty(self):
        if self.product_id:
            primary_packaging_id = self.env['product.packaging'].search(
                [('product_id', '=', self.product_id.id), ('primary_unit', '=', True)])
            self.product_packaging_id = primary_packaging_id.id
            self.product_packaging_qty = 1

    @api.onchange('product_id', 'product_uom_qty')
    def _onchange_status(self):
        #warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)])
        if self.product_id:
            # primary_packaging_id = self.env['product.packaging'].search(
            # 	[('product_id', '=', self.product_id.id), ('primary_unit', '=', True)])
            # self.product_packaging_id = primary_packaging_id.id
            stock_quant = self.env['stock.quant'].search(
                [('product_id', '=', self.product_id.id), ('location_id', '=', self.order_id.picking_type_id.default_location_src_id.id)])
            total_stock = 0
            if stock_quant:
                for stock in stock_quant:
                    total_stock += stock.quantity
                if self.product_uom_qty < total_stock:
                    self.qty_status = False
                else:
                    self.qty_status = True
            else:
                self.qty_status = True

    @api.depends('price_unit', 'product_uom_qty')
    def _compute_total_amount(self):
        for line in self:
            line.actaul_price = line.price_unit * line.product_uom_qty

    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_pricelist_item_id(self):
        for line in self:
            if not line.product_id or line.display_type or not line.order_id.pricelist_id:
                line.pricelist_item_id = False
            else:
                pricelists = line.compute_price_rule_get_package_items \
                    (line.order_id.date_order, [line.product_id.product_tmpl_id.id], line.order_id.pricelist_id.id,
                     line.product_packaging_id.id)
                if pricelists:
                    line.pricelist_item_id = pricelists[0].id
                else:
                    line.pricelist_item_id = False
                    # raise UserError("Product not added under the pricelist.")

class SaleOrderLineInh(models.Model):
    _inherit = 'sale.order.line'

    pkg_unit_price = fields.Float("PKG Unit Price")


class SaleAdvancePaymentInh(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def _create_invoice(self, order, so_line, amount):
        if order.partner_id.bill_type == 'bill_to_bill':
            invoice = self.env['account.move'].search(
                [('partner_id', '=', order.partner_id.id), ('move_type', '=', 'out_invoice')])
            for inv in invoice:
                if inv.payment_state == 'not_paid' and False:
                    raise UserError(_('There are unpaid Invoices for the Customer.'))
        return super(SaleAdvancePaymentInh, self)._create_invoice(order, so_line, amount)

    # override--to include journal of sale category
    def _prepare_invoice_values(self, order, name, amount, so_line):
        default_sales_account = False
        if order.pricelist_id.special and order.journal_id:
            default_sales_account = order.journal_id.default_account_id and order.journal_id.default_account_id.id
        invoice_vals = {
            'ref': order.client_order_ref,
            'move_type': 'out_invoice',
            'invoice_origin': order.name,
            'invoice_user_id': order.user_id.id,
            'narration': order.note,
            'partner_id': order.partner_invoice_id.id,
            'fiscal_position_id': (order.fiscal_position_id or order.fiscal_position_id.get_fiscal_position(
                order.partner_id.id)).id,
            'partner_shipping_id': order.partner_shipping_id.id,
            'currency_id': order.pricelist_id.currency_id.id,
            'payment_reference': order.reference,
            'invoice_payment_term_id': order.payment_term_id.id,
            'partner_bank_id': order.company_id.partner_id.bank_ids[:1].id,
            'team_id': order.team_id.id,
            'campaign_id': order.campaign_id.id,
            'medium_id': order.medium_id.id,
            'source_id': order.source_id.id,
            'invoice_line_ids': [(0, 0, {
                'name': name,
                'price_unit': amount,
                'quantity': 1.0,
                'product_id': self.product_id.id,
                'product_uom_id': so_line.product_uom.id,
                'tax_ids': [(6, 0, so_line.tax_id.ids)],
                'sale_line_ids': [(6, 0, [so_line.id])],
                'account_id': default_sales_account or False,
                # 'analytic_tag_ids': [(6, 0, so_line.analytic_tag_ids.ids)],
                # 'analytic_account_id': order.analytic_account_id.id or False,
                'analytic_distribution': so_line.analytic_distribution,
            })],
        }
        if order.sales_category:
            invoice_vals['journal_id'] = order.sales_category.journal.id
        return invoice_vals


class SaleCategory(models.Model):
    _name = "sales.category"
    _description = "Sale Category"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "category"

    category = fields.Char()
    journal = fields.Many2one('account.journal')


class DocAttachmentCl(models.Model):
    _inherit = 'ir.attachment'

    lpo_attach_rel = fields.Many2many('sale.order', 'lpo_attach_id', 'attach_id99', 'doc_id88',
                                      string="LPO Attachment", invisible=1)

    # @api.model
    # def check(self, mode, values=None):
    #     """ Restricts the access to an ir.attachment, according to referred mode """
    #     if self.env.is_superuser():
    #         return True
    #     # Always require an internal user (aka, employee) to access to a attachment
    #     if not (self.env.is_admin() or self.env.user._is_internal()):
    #         raise AccessError(_("Sorry, you are not allowed to access this document."))
    #     # collect the records to check (by model)
    #     model_ids = defaultdict(set)            # {model_name: set(ids)}
    #     if self:
    #         # DLE P173: `test_01_portal_attachment`
    #         self.env['ir.attachment'].flush_model(['res_model', 'res_id', 'create_uid', 'public', 'res_field'])
    #         self._cr.execute('SELECT res_model, res_id, create_uid, public, res_field FROM ir_attachment WHERE id IN %s', [tuple(self.ids)])
    #         for res_model, res_id, create_uid, public, res_field in self._cr.fetchall():
    #             if public and mode == 'read':
    #                 continue
    #             if not self.env.is_system():
    #                 if not res_id:
    #                     raise AccessError(_("Sorry, you are not allowed to access this document."))
    #                 if res_field:
    #                     field = self.env[res_model]._fields[res_field]
    #                     if field.groups:
    #                         if not self.env.user.user_has_groups(field.groups):
    #                             raise AccessError(_("Sorry, you are not allowed to access this document."))
    #             if not (res_model and res_id):
    #                 continue
    #             model_ids[res_model].add(res_id)
    #     if values and values.get('res_model') and values.get('res_id'):
    #         model_ids[values['res_model']].add(values['res_id'])
    #
    #     # check access rights on the records
    #     for res_model, res_ids in model_ids.items():
    #         # ignore attachments that are not attached to a resource anymore
    #         # when checking access rights (resource was deleted but attachment
    #         # was not)
    #         if res_model not in self.env:
    #             continue
    #         if res_model == 'res.users' and len(res_ids) == 1 and self.env.uid == list(res_ids)[0]:
    #             # by default a user cannot write on itself, despite the list of writeable fields
    #             # e.g. in the case of a user inserting an image into his image signature
    #             # we need to bypass this check which would needlessly throw us away
    #             continue
    #         records = self.env[res_model].browse(res_ids).exists()
    #         # For related models, check if we can write to the model, as unlinking
    #         # and creating attachments can be seen as an update to the model
    #         access_mode = 'write' if mode in ('create', 'unlink') else mode
    #         records.check_access_rights(access_mode)
    #         records.check_access_rule(access_mode)


class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    sale_order_id = fields.Many2one('sale.order', string="Sale Order")
    sale_order_customer_id = fields.Many2one('res.partner', string="Sale Order Customer",
                                             store=True)

    @api.constrains('sale_order_customer_id')
    def _check_sale_order_customer_id(self):
        for rec in self:
            if rec.move_type in ('out_invoice', 'out_refund'):
                if not rec.sale_order_customer_id:
                    if rec.sale_order_id.exists():
                        rec.sale_order_customer_id = rec.sale_order_id.partner_id
                    else:
                        rec.sale_order_customer_id = rec.partner_id


class AccountMoveLineInherit(models.Model):
    _inherit = 'account.move.line'

    sale_order_customer_id = fields.Many2one(related='move_id.sale_order_customer_id', string="Sale Order Customer",
                                             store=True)


class StockQuantInherit(models.Model):
    _inherit = 'stock.quant'

    kg_cost_price = fields.Float('Cost Price', compute='_compute_cost_price')
    kg_lot_expiry_date = fields.Datetime(related='lot_id.expiration_date')

    @api.depends('value', 'quantity')
    def _compute_cost_price(self):
        for rec in self:
            rec.kg_cost_price = rec.value / rec.quantity if rec.quantity else 0


    @api.depends('location_id', 'lot_id', 'lot_id.expiration_date', 'package_id', 'owner_id')
    def _compute_display_name(self):
        """name that will be displayed in the detailed operation"""
        for record in self:
            name = [record.location_id.display_name]
            if record.lot_id:
                name.append(record.lot_id.name)
                if record.expiration_date:
                    # Convert expiration_date to user's local time
                    user_tz = self.env.user.tz or 'UTC'  # Default to UTC if no timezone is set
                    local_tz = timezone(user_tz)
                    expiration_date_utc = record.expiration_date.replace(tzinfo=UTC)
                    expiration_date_local = expiration_date_utc.astimezone(local_tz)
                    expiration_date_str = expiration_date_local.strftime('%d-%m-%Y')
                    name.append(expiration_date_str)
            if record.package_id:
                name.append(record.package_id.name)
            if record.owner_id:
                name.append(record.owner_id.name)
            record.display_name = ' - '.join(name)

