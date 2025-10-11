from odoo import models, fields, _, api, SUPERUSER_ID
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_round, float_is_zero, groupby
from datetime import date

from datetime import datetime, timedelta,date
import time

SPLIT_METHOD = [
    ('equal', 'Equal'),
    ('by_quantity', 'By Quantity'),
    ('by_current_cost_price', 'By Current Cost'),
    ('by_weight', 'By Weight'),
    ('by_volume', 'By Volume'),
]

class ShipmentAdviceLandedCost(models.Model):
    _name = 'shipment.advice.landed.cost'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'shipment_advice_id'

    shipment_advice_id = fields.Many2one('shipment.advice', string="Shipment Advice")
    partner_id = fields.Many2one('res.partner', string="Vendor")
    document_file_name = fields.Char('File Name')
    document_file = fields.Binary("File")
    date_added = fields.Datetime(string='Invoice Date', required=True, readonly=True, index=True, copy=False,
                                 default=fields.Datetime.now)
    inv_no = fields.Char(string='Invoice No.')
    landed_cost_lines = fields.One2many(comodel_name='shipment.advice.landed.cost.line', inverse_name='landed_cost_id',
                                     string='Lines', required=False, tracking=True)
    state = fields.Selection([('new', 'New'), ('submitted', 'Submitted to Finance'), ('applied', 'Applied')],
                             string='Status', default='new', tracking=True)
    total_amount = fields.Float(string='Total',  compute='get_total_amount', tracking=True)
    move_id = fields.Many2one('account.move', string="Landed Cost")
    purchase_order_ids = fields.Many2many('purchase.order', 'sa_landed_cost_purchase', 'landed_cost_id', 'purchase_id')

    bl_entry_id = fields.Many2one(related="shipment_advice_id.bl_entry_id")
    bl_entry_container_id = fields.Many2one(related="shipment_advice_id.bl_entry_container_id")
    l10n_in_gst_treatment = fields.Selection([
        ('regular', 'Registered Business - Regular'),
        ('composition', 'Registered Business - Composition'),
        ('unregistered', 'Unregistered Business'),
        ('consumer', 'Consumer'),
        ('overseas', 'Overseas'),
        ('special_economic_zone', 'Special Economic Zone'),
        ('deemed_export', 'Deemed Export'),
        ('uin_holders', 'UIN Holders'),
    ], string="GST Treatment")
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company', related='bl_entry_id.company_id', store=True)
    inv_no = fields.Char("Inv No")

    customs_cost_lines = fields.One2many('bl.entry.cost.customs', 'sa_landed_cost_id', string="Customs Cost Lines")

    show_customs_cost = fields.Boolean("Show Customs Cost", compute='_compute_show_customs_cost')


    def _compute_show_customs_cost(self):

        for cost in self:
            show_customs_cost = False
            if cost.customs_cost_lines:
                show_customs_cost = True
            cost.show_customs_cost = show_customs_cost



    def write(self, vals):
        res = super(ShipmentAdviceLandedCost, self).write(vals)

        for landed_cost in self:
            message = ""
            for line in landed_cost.landed_cost_lines:
                    message = "%s <br/> %s : %s : %s" % (message, line.product_id.name, str(line.split_method), line.total_amount)

            landed_cost.message_post(
                body=message, subtype_id=self.env.ref("mail.mt_comment").id
            )

        return res

    def create(self, vals):

        res = super(ShipmentAdviceLandedCost, self).create(vals)

        for landed_cost in res:
            message = ""
            for line in landed_cost.landed_cost_lines:
                message = "%s <br/> %s : %s : %s" % (
                message, line.product_id.name, str(line.split_method), line.total_amount)

            landed_cost.message_post(
                body=message, subtype_id=self.env.ref("mail.mt_comment").id
            )
            if landed_cost.partner_id:
                landed_cost.l10n_in_gst_treatment = landed_cost.partner_id.l10n_in_gst_treatment

        return res





    def unlink(self):
        for rec in self:
            if rec.state != 'new' and False:
                raise UserError(_('You cannot delete landed cost which is not in new status'))
        return super(ShipmentAdviceLandedCost, self).unlink()


    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.l10n_in_gst_treatment = self.partner_id.l10n_in_gst_treatment
        else:
            self.l10n_in_gst_treatment = False


    def get_landed_cost_journal(self):
        # Find Journal for posting Landed Cost
        company = self.env.company
        domain = [
            *self.env['account.journal']._check_company_domain(company),
            ('type', '=', 'purchase'),
        ]
        journal = self.env['account.journal'].search(domain, limit=1)
        return journal


    def apply_landed_cost(self):

        moves = self.env['account.move']
        for rec in self:

            move_type = 'in_invoice'
            #journal = self.get_landed_cost_journal()
            if not rec.l10n_in_gst_treatment:
                raise UserError("GST Treatment detail missing!")

            invoice_vals = {
                'ref': rec.shipment_advice_id.bl_entry_id.name + '/' + rec.shipment_advice_id.bl_entry_container_id.container_number + '/' + str(rec.inv_no),
                'move_type': move_type,
                'narration': rec.shipment_advice_id.name,
                'currency_id': self.env.company.currency_id.id,
                'invoice_user_id': self.env.user.id,
                'partner_id': rec.partner_id.id,
                'invoice_line_ids': [],
                'company_id': self.env.company.id,
                'invoice_date': rec.date_added,
                'date': date.today(),
                'shipment_id' : rec.shipment_advice_id.id,
                'l10n_in_gst_treatment' : rec.l10n_in_gst_treatment,
                'invoice_payment_term_id': rec.partner_id.property_supplier_payment_term_id.id,
            }

            invoice_line_ids = []
            for line in rec.landed_cost_lines:
                line_vals = {
                    'name': line.description,
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_id.uom_id.id,
                    'quantity': 1,
                    'price_unit': line.amount,
                    'tax_ids': [(6, 0, line.tax_ids.ids)],
                    'is_landed_costs_line' : True,
                    'shipment_advice_landed_cost_line_id' : line.id,
                    'account_id' : line.account_id.id
                }
                invoice_line_ids.append((0, 0, line_vals))

            #for customs cost

            for customs in rec.customs_cost_lines:

                custom_duty_product = self.env['product.product'].search([('is_a_custom_duty', '=', True)], limit=1)

                if not custom_duty_product:
                    raise UserError("Custom Duty product is missing, Please check product with 'Is this custom duty?'")


                description = "%s, %s" % (customs.container_id.container_number, customs.product_id.name)
                line_vals = {
                    'name': description,
                    'product_id': custom_duty_product.id,
                    'product_uom_id': custom_duty_product.uom_id.id,
                    'quantity': 1,
                    'price_unit': customs.total_amount_landed_cost,
                    'tax_ids': [(6, 0, customs.tax_ids.ids)],
                    'is_landed_costs_line': True,
                    'bl_entry_custom_cost': customs.id,
                    'account_id': customs.account_id.id
                }
                invoice_line_ids.append((0, 0, line_vals))

            invoice_vals['invoice_line_ids'] = invoice_line_ids
            invoice = moves.create(invoice_vals)

            if rec.customs_cost_lines:

                tax_wise_custom_duty = {}
                #Find tax wise total
                for costoms_cost in rec.customs_cost_lines:
                    if costoms_cost.tax_ids:
                        if costoms_cost.tax_ids.name not in tax_wise_custom_duty:
                            tax_wise_custom_duty[costoms_cost.tax_ids.name] = costoms_cost.vat_amount
                        else:
                            tax_wise_custom_duty[costoms_cost.tax_ids.name] += costoms_cost.vat_amount

                tax_line = invoice.line_ids.filtered(lambda line: line.tax_line_id)
                if not tax_line:
                    raise ValueError("No tax line found in the bill.")

                for t_line in tax_line:
                    if t_line.name in tax_wise_custom_duty:
                        amount = tax_wise_custom_duty.get(t_line.name)
                        t_line.write({
                            'debit': amount,
                            'credit': 0.0,
                        })



            invoice.action_post()
            rec.move_id = invoice.id
            rec.state = 'applied'
            invoice.button_create_landed_costs()
            #Compute and apply after discount amount in lot and serial numbers
            rec.shipment_advice_id.update_after_discount_cost()


    def get_total_amount(self):
        for rec in self:
            total_amount = 0
            for line in rec.landed_cost_lines:
                total_amount += line.total_amount
            for cost in rec.customs_cost_lines:
                total_amount += cost.total_amount_landed_cost
            rec.total_amount = total_amount

    def submit_landed_cost(self):
        for rec in self:
            rec.state = 'submitted'
            rec.mail_notification_to_accounts()

    def mail_notification_to_accounts(self):

        bl_no = self.shipment_advice_id.bl_entry_id and self.shipment_advice_id.bl_entry_id.name or self.shipment_advice_id.bill_no

        mail_content = "  Hello,<br>Please apply landed Cost to Shipment Advice Number" + str(self.shipment_advice_id.name) + \
                       "<br>Shipment No : " + str(self.shipment_advice_id.shipment_no) + \
                       "<br>BL No : " + str(bl_no) + \
                       "<br>From vendor : " + str(self.partner_id.name) +\
                       "<br>for Amount : " + str(self.total_amount)

        users = self.env.ref('kg_sarya_inventory.can_apply_landed_cost').users
        email_to = ""
        for usr in users:
            if usr.partner_id.email:
                if not email_to:
                    email_to = usr.partner_id.email
                else:
                    email_to = email_to + ', ' + usr.partner_id.email

        main_content = {
            'subject': _('Landed Cost to Aplly for Shipment Advice Number : %s' % (self.shipment_advice_id.name)),
            'author_id': self.env.user.partner_id.id,
            'body_html': mail_content,
            'email_to': email_to,
        }
        self.env['mail.mail'].sudo().create(main_content).send()


class ShipmentAdviceLandedCostLine(models.Model):
    _name = 'shipment.advice.landed.cost.line'

    landed_cost_id = fields.Many2one('shipment.advice.landed.cost', string="Vendor")

    product_id = fields.Many2one('product.product', string="Cost")
    description = fields.Char('Description')
    amount = fields.Float('Amount')
    tax_ids = fields.Many2one('account.tax', string="VAT")
    total_amount = fields.Float('Total')

    split_method = fields.Selection(
        SPLIT_METHOD,
        string='Split Method',
        required=True,
        help="Equal : Cost will be equally divided.\n"
             "By Quantity : Cost will be divided according to product's quantity.\n"
             "By Current cost : Cost will be divided according to product's current cost.\n"
             "By Weight : Cost will be divided depending on its weight.\n"
             "By Volume : Cost will be divided depending on its volume.")
    account_id = fields.Many2one('account.account', 'Account', domain=[('deprecated', '=', False)])

    bl_entry_cost = fields.Many2one('bl.entry.cost', 'Bl Entry Cost')

    date_added = fields.Datetime(string='Invoice Date', default=fields.Datetime.now)

    inv_no = fields.Char("Inv No")

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            line.description = line.product_id.name
            accounts_data = line.product_id.product_tmpl_id.get_product_accounts()
            line.split_method = line.product_id.split_method_landed_cost
            line.account_id = accounts_data['expense']


    @api.onchange('amount', 'tax_ids')
    def _onchange_amount_tax(self):
        for line in self:
            taxes = line.tax_ids.compute_all(
                line.amount,
                currency=self.env.company.currency_id,
                quantity=1.0
            )
            line.total_amount = taxes.get('total_included')


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    shipment_advice_landed_cost_line_id = fields.Many2one('shipment.advice.landed.cost.line', string="Landed Cost Line", copy=False)

    bl_entry_custom_cost = fields.Many2one('bl.entry.cost.customs', string="Bl entry customs cost", copy=False)


# class AccountMove(models.Model):
#     _inherit = 'account.move'
#
#
#     def button_create_landed_costs(self):
#         """Create a `stock.landed.cost` record associated to the account move of `self`, each
#         `stock.landed.costs` lines mirroring the current `account.move.line` of self.
#         """
#         self.ensure_one()
#         landed_costs_lines = self.line_ids.filtered(lambda line: line.is_landed_costs_line)
#
#         landed_costs = self.env['stock.landed.cost'].with_company(self.company_id).create({
#             'vendor_bill_id': self.id,
#             'cost_lines': [(0, 0, {
#                 'product_id': l.product_id.id,
#                 'name': l.product_id.name,
#                 'account_id': l.product_id.product_tmpl_id.get_product_accounts()['stock_input'].id,
#                 'price_unit': l.currency_id._convert(l.price_subtotal, l.company_currency_id, l.company_id, l.move_id.date),
#                 'split_method': l.product_id.split_method_landed_cost or 'equal',
#                 'bl_custom_id': l.bl_entry_custom_cost and l.bl_entry_custom_cost.id or False
#             }) for l in landed_costs_lines],
#         })
#         action = self.env["ir.actions.actions"]._for_xml_id("stock_landed_costs.action_stock_landed_cost")
#         return dict(action, view_mode='form', res_id=landed_costs.id, views=[(False, 'form')])








