# -*- coding: utf-8 -*-

from odoo import models, fields, _, api, SUPERUSER_ID
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta,date
import time

SPLIT_METHOD = [
    ('equal', 'Equal'),
    ('by_quantity', 'By Quantity'),
    ('by_current_cost_price', 'By Current Cost'),
    ('by_weight', 'By Weight'),
    ('by_volume', 'By Volume'),
]

class BlEntry(models.Model):
    _name = 'bl.entry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Shipment Advice'
    _rec_name = 'name'
    _order = 'name desc, id desc'

    name = fields.Char(string='BL Number', required=True, copy=False)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', 'Responsible', copy=False, default=lambda self: self.env.user, required=True, tracking=True)
    state = fields.Selection(string='Status', selection=[('draft', 'Draft'),
                                                         ('container', 'Container Details'),
                                                         ('procurement_approval', 'Procurement Approval'),
                                                         ('finance_approval', 'Finance Approval'),
                                                         ('confirm', 'Confirm'),
                                                         ('close', 'Close')], required=True, tracking=True, default='draft')
    bl_date = fields.Date('Invoice Date', tracking=True)
    number_of_container = fields.Integer("Number of Container", compute="_compute_number_of_container")
    bl_entry_container_ids = fields.One2many('bl.entry.container', 'bl_entry_id', 'Containers')

    purchase_ids = fields.Many2many('purchase.order', 'bl_entry_purchase_order', "bl_entry_id", "purchase_id",
                                    required=True, copy=False,
                                    domain="[('state', 'in', ('purchase', 'done')), "
                                           "('stock_type', '=', 'inventory'), "
                                           "('shipping_status', '!=', 'complete'),"
                                           "('finance_waiting_approval', '=', False),"
                                           "('is_pi_qty_entered', '=', True),"
                                           "('bl_id', '=', False),"
                                           "('bl_number', '!=', False),"
                                           "('is_shipping_documents_uploaded', '=', True)"
                                           "]")

    vendor_id = fields.Many2one('res.partner', string="Vendor")

    bl_entry_lines = fields.One2many('bl.entry.lines', 'bl_entry_id', 'Container Details')

    bl_entry_costs = fields.One2many('bl.entry.cost', 'bl_entry_id', 'Cost Details')

    bl_entry_costs_customs = fields.One2many('bl.entry.cost.customs', 'bl_entry_id', 'Cost Customs')


    customs_bill_date = fields.Date('Customs Bill Date', tracking=True)

    customs_vendor_id = fields.Many2one('res.partner', string="Customs Vendor")

    customs_inv_number = fields.Char(string="Customs Invoice Number")




    is_price_not_matching = fields.Boolean("Is price not matching")
    is_qty_not_matching = fields.Boolean("Is Qty not matching")

    price_not_matching_reason = fields.Char("Price not matching Reason")

    shipment_advices = fields.One2many('shipment.advice', 'bl_entry_id', 'Shipment Advice')

    shipment_advice_count = fields.Integer('Shipment Advice Count', compute='_compute_count')

    is_pending_to_invoice = fields.Boolean("Pending to Invoice", compute='_find_pending_to_invoice')

    attachment_ids = fields.One2many('partner.attachments', 'bl_id', string='Attachments', tracking=True)

    shipment_no = fields.Char('Commercial Invoice No', copy=False, tracking=True)



    boe_number = fields.Char('BOE', copy=False, tracking=True)
    zdlm = fields.Char('ZDLM', copy=False, tracking=True)

    boe_date = fields.Date('BOE Date', tracking=True)

    notes = fields.Char("Notes")

    invoice_ids = fields.Many2many('account.move', 'bl_entry_invoices', "bl_entry_id", "move_id", copy=False)

    container_type = fields.Selection(string='Container Type',
                                      selection=[('reefer_chilled', 'Reefer Chilled'),
                                                 ('reefer_frozen', 'Reefer Frozen'),
                                                 ('dry', 'Dry'), ('air', 'Air')], copy=False)

    container_volume = fields.Selection(string='Container Volume',
                                        selection=[('40_feet', '40 Feet'), ('20_feet', '20 Feet'), ('dry', 'Other')],
                                        copy=False)

    document_missing = fields.Char(string="Document Status", compute='_find_document_missing')

    clearing_agent = fields.Many2one('res.partner', string="Clearing Agent")
    is_docs_send_to_agent = fields.Boolean("Is documents send to clearing Agent")

    doc_clearing_agent = fields.Many2one('res.partner', string="Freight Forwarder")

    departure_date = fields.Date('Departure Date', tracking=True)
    expected_date = fields.Date('Expected Date', tracking=True)

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

    foc_credit_account_id = fields.Many2one('account.account', string="FOC Credit Account")

    total_price = fields.Float('Total Price', compute='_compute_total_price')
    currency_id = fields.Many2one('res.currency', string="Currency", compute='_compute_po_currency')

    is_stock_unloaded_in_outside_warehouse = fields.Boolean("Is stock unloaded in outside warehouse?")

    po_type = fields.Selection(string='PO Type', selection=[('import', 'Import'), ('local', 'Local')], default='import')

    lock_cost_entry = fields.Boolean("Cost Entry Locked?", default=False)

    po_qty = fields.Float("PO Qty", compute='_compute_po_qty')
    po_foc_qty = fields.Float("PO FOC Qty", compute='_compute_po_qty')

    def _compute_po_qty(self):
        for rec in self:
            po_qty = 0
            po_foc_qty = 0
            for po in rec.purchase_ids:
                for po_line in po.order_line:
                    po_qty += po_line.product_packaging_qty
                    po_foc_qty += po_line.pi_foc_qty

            rec.po_qty = po_qty
            rec.po_foc_qty = po_foc_qty


    def do_procurement_approval(self):

        for rec in self:
            if rec.is_price_not_matching:
                rec.state = 'finance_approval'

                subject = 'BL price difference Approval Pending %s %s' % (rec.vendor_id.name, rec.name)
                mail_content = " Hello,<br> Price in BL is not matching for following items : "
                for item in rec.bl_entry_lines:
                    if item.is_price_not_matching:
                        mail_content = "%s <br> Item: %s" % (mail_content, item.product_id.name)

                users = self.env.ref('kg_sarya_inventory.can_approve_commercial_invoice_wms').users
                email_to = ""
                for usr in users:
                    if usr.partner_id.email:
                        if not email_to:
                            email_to = usr.partner_id.email
                        else:
                            email_to = email_to + ', ' + usr.partner_id.email

                main_content = {
                    'subject': _(subject),
                    'author_id': self.env.user.partner_id.id,
                    'body_html': mail_content,
                    'email_to': email_to,
                }
                self.env['mail.mail'].sudo().create(main_content).send()

            else:
                rec.state = 'confirm'
                rec.gen_landed_cost_estimate()

                subject = 'BL is Approved %s %s' % (rec.vendor_id.name, rec.name)
                mail_content = " Hello,<br> BL %s is approved." % rec.name
                users = self.env.ref('kg_sarya_inventory.get_bl_approval_notification').users
                email_to = ""
                for usr in users:
                    if usr.partner_id.email:
                        if not email_to:
                            email_to = usr.partner_id.email
                        else:
                            email_to = email_to + ', ' + usr.partner_id.email

                main_content = {
                    'subject': _(subject),
                    'author_id': self.env.user.partner_id.id,
                    'body_html': mail_content,
                    'email_to': email_to,
                }
                self.env['mail.mail'].sudo().create(main_content).send()


    def gen_landed_cost_estimate(self):

        if self.po_type == 'import':

            clearing_agent = self.clearing_agent
            freight_forwarder = self.doc_clearing_agent

            from_port = False
            to_port = False

            for po in self.purchase_ids:
                from_port = po.port_of_loading
                to_port = po.port_of_discharge

            if not from_port:
                raise UserError(_("Please check port of loading is configured in PO"))

            if not to_port:
                raise UserError(_("Please check port of discharge is configured in PO"))

            if not clearing_agent:
                raise UserError(_("Please select Clearing Agent"))
            if not freight_forwarder:
                raise UserError(_("Please select Freight Forwarder"))

            estimation = self.env['fright.charge.estimation'].search([('vendor_id', '=', freight_forwarder.id),
                                                                      ('from_port', '=', from_port.id),
                                                                      ('to_port', '=', to_port.id)], limit=1)

            if not estimation:
                raise UserError(_("Please contact Finance to configure fright estimation for %s, From Port : %s, To Port %s" % (freight_forwarder.name,
                                                                    from_port.name, to_port.name)))


            #Generate custom Duty Estimate

            custom_duty = self.env['product.product'].search([('is_a_custom_duty', '=', True)], limit=1)
            if not custom_duty:
                raise UserError(_("Custom duty product is not configured"))

            custom_duty_amount = self.computed_estimated_custom_duty()

            taxes = custom_duty.supplier_taxes_id.compute_all(
                custom_duty_amount,
                currency=self.env.company.currency_id,
                quantity=1.0
            )
            custom_duty_amount_total = taxes.get('total_included')

            if custom_duty_amount_total > 0:
                accounts_data = custom_duty.product_tmpl_id.get_product_accounts()
                vals = {'bl_entry_id': self.id,
                        'product_id': custom_duty.id,
                        'partner_id' : clearing_agent.id,
                        'amount': custom_duty_amount,
                        'total_amount': custom_duty_amount_total,
                        'tax_ids':  custom_duty.supplier_taxes_id and custom_duty.supplier_taxes_id.id or False,
                        'split_method': custom_duty.split_method_landed_cost,
                        'account_id': accounts_data['expense'].id,
                        'type': 'estimation'}
                self.env['bl.entry.cost'].create(vals)

            # Generate FREIGHT CHARGES Estimate
            freight_charge = self.env['product.product'].search([('is_a_freight_charge', '=', True)], limit=1)
            if not freight_charge:
                raise UserError(_("Freight charge product is not configured"))

            accounts_data = freight_charge.product_tmpl_id.get_product_accounts()

            taxes = freight_charge.supplier_taxes_id.compute_all(
                estimation.fright_charge * self.number_of_container,
                currency=self.env.company.currency_id,
                quantity=1.0
            )
            total_amount = taxes.get('total_included')

            vals = {'bl_entry_id': self.id,
                    'product_id': freight_charge.id,
                    'partner_id': freight_forwarder.id,
                    'amount': estimation.fright_charge * self.number_of_container,
                    'tax_ids': freight_charge.supplier_taxes_id and freight_charge.supplier_taxes_id.id or False,
                    'total_amount': total_amount,
                    'split_method': freight_charge.split_method_landed_cost,
                    'account_id': accounts_data['expense'].id,
                    'type': 'estimation'}
            self.env['bl.entry.cost'].create(vals)


    def computed_estimated_custom_duty(self, estimation=None):

        #Not required for KSA custom duty calculation
        if not estimation and False:
            clearing_agent = self.clearing_agent
            from_port = False
            to_port = False

            for po in self.purchase_ids:
                from_port = po.port_of_loading
                to_port = po.port_of_discharge

            if not from_port:
                raise UserError(_("Please check port of loading is configured in PO"))

            if not to_port:
                raise UserError(_("Please check port of discharge is configured in PO"))

            estimation = self.env['fright.charge.estimation'].search([('vendor_id', '=', clearing_agent.id),
                                                                      ('from_port', '=', from_port.id),
                                                                      ('to_port', '=', to_port.id)], limit=1)

            if not estimation:
                raise UserError(_("Please contact Finance to configure fright estimation for %s, From Port : %s, To Port %s" % (clearing_agent.name,
                                                                                from_port.name, to_port.name)))


        item_wise_qty_mapping = {}
        for bl_line in self.bl_entry_lines:

            total_amount = bl_line.bl_total_price
            product_id = bl_line.product_id

            # Convert to company currency

            company_currency_amount = bl_line.currency_id._convert(total_amount,
                                                                   self.env.company.currency_id, self.env.company,
                                                                   fields.Date.today())

            if product_id in item_wise_qty_mapping:
                item_wise_qty_mapping[product_id] += company_currency_amount
            else:
                item_wise_qty_mapping[product_id] = company_currency_amount

        custom_duty = 0

        '''Activate below calculation for KSA'''
        ksa = True
        if ksa:

            #Product wise custom duty calculated
            #Maximum of 750 SAR is added as the other charge

            for product_id in item_wise_qty_mapping:
                company_currency_amount = item_wise_qty_mapping[product_id]
                if product_id.landed_cost_custom_duty_perc > 0.001:
                    custom_duty += company_currency_amount * (product_id.landed_cost_custom_duty_perc /100)

            custom_duty = custom_duty

        '''Activate below calculation for UAE'''
        uae = False
        if uae:
            '''
               FRT =  No Container * Estimated Shipping Cost
               INS = 1 % of (FRT + BL Value)
               Custom Duty = 5 % of (FRT + INS + BL Value)
               
               Fixed Cost
               RGCH 70
               KDID 20
               ARCH 5
            '''
            bl_value = 0
            for product_id in item_wise_qty_mapping:
                bl_value += item_wise_qty_mapping[product_id]

            frt = self.number_of_container * estimation.container_cost
            ins = (frt + bl_value) * 0.01
            custom_duty = (frt + ins + bl_value) * 0.05

            custom_duty = custom_duty + 70 + 20 + 5

        return custom_duty


    def mark_container_entry_completed(self):

        for rec in self:

            rec.check_bl_qty()

            bl_is_price_not_matching = False
            rec.price_not_matching_reason = ""

            # Find any mismatch on the product pricing and commercial invoice
            for line in rec.bl_entry_lines:
                is_price_not_matching = False

                # Check zero price
                if line.bl_price == 0:
                    is_price_not_matching = True
                    bl_is_price_not_matching = True

                # Check Weather pricing is matching with contract
                if line.bl_price > line.price_after_fixed_discount:
                    is_price_not_matching = True
                    bl_is_price_not_matching = True

                line.is_price_not_matching = is_price_not_matching

            rec.is_price_not_matching = bl_is_price_not_matching


            if rec.vendor_id.do_mandatory_procurement_approval_required or rec.is_price_not_matching or rec.is_qty_not_matching:

                rec.state = "procurement_approval"
                price_not_matching_reason = ""

                if rec.is_price_not_matching:
                    subject = 'BL price difference Approval Pending %s %s' % (rec.vendor_id.name, rec.name)
                    mail_content = " Hello,<br> Price in BL is not matching for following items : "
                    for item in rec.bl_entry_lines:
                        if item.is_price_not_matching:
                            mail_content = "%s <br> Item: %s" % (mail_content, item.product_id.name)
                            price_not_matching_reason = "%s, %s" % (price_not_matching_reason, item.product_id.name)
                elif rec.is_qty_not_matching:
                    subject = 'BL Qty is not Matching Approval Pending %s %s' % (rec.vendor_id.name, rec.name)
                    mail_content = " Hello,<br> BL Qty is not Matching. Please check bl log note for item details"

                else:
                    subject = 'BL Approval Pending %s %s' % (rec.vendor_id.name, rec.name)
                    mail_content = " Hello,<br> Please approve BL"

                users = self.env.ref('kg_sarya_inventory.do_bl_procurement_approval').users
                email_to = ""
                for usr in users:
                    if usr.partner_id.email:
                        if not email_to:
                            email_to = usr.partner_id.email
                        else:
                            email_to = email_to + ', ' + usr.partner_id.email


                main_content = {
                    'subject': _(subject),
                    'author_id': self.env.user.partner_id.id,
                    'body_html': mail_content,
                    'email_to': email_to,
                }
                self.env['mail.mail'].sudo().create(main_content).send()


                rec.price_not_matching_reason = price_not_matching_reason
            else:
                rec.gen_landed_cost_estimate()
                rec.state = "confirm"

                users = self.env.ref('kg_sarya_inventory.bl_notification_after_approval').users
                email_to = ""
                for usr in users:
                    if usr.partner_id.email:
                        if not email_to:
                            email_to = usr.partner_id.email
                        else:
                            email_to = email_to + ', ' + usr.partner_id.email

                main_content = {
                    'subject': _('India: BL %s is confirmed' % rec.name),
                    'author_id': self.env.user.partner_id.id,
                    'body_html': 'Hi,<br>BL %s is confirmed' % rec.name,
                    'email_to': email_to,
                }
                self.env['mail.mail'].sudo().create(main_content).send()



    def check_bl_qty(self):

        for bl in self:

            qty_mismatch_msg = ""

            po_item_wise_qty = {}
            for po in bl.purchase_ids:
                for po_line in po.order_line:
                    product_id = po_line.product_id.id
                    pi_qty = po_line.pi_qty
                    pi_foc_qty = po_line.pi_foc_qty
                    if product_id in po_item_wise_qty:
                        po_item_wise_qty[product_id]['pi_qty'] += pi_qty
                        po_item_wise_qty[product_id]['foc_qty'] += pi_foc_qty
                    else:
                        po_item_wise_qty[product_id] = {'pi_qty' : pi_qty,
                                                       'foc_qty' : pi_foc_qty}


            bl_item_wise_qty = {}
            for bl_line in bl.bl_entry_lines:
                for details in bl_line.qty_details:
                    product_id = bl_line.product_id.id
                    qty = details.qty_to_receive
                    foc_qty = details.foc_qty

                    if product_id in bl_item_wise_qty:
                        bl_item_wise_qty[product_id]['qty'] += qty
                        bl_item_wise_qty[product_id]['foc_qty'] += foc_qty
                    else:
                        bl_item_wise_qty[product_id] = {'qty': qty,
                                                        'foc_qty': foc_qty}


            for product_id in po_item_wise_qty:

                if product_id not in bl_item_wise_qty:
                    bl.is_qty_not_matching = True
                    qty_mismatch_msg = "%s Item Missing : %s," % (qty_mismatch_msg, self.env['product.product'].browse(product_id).name)
                else:
                    pi_qty = po_item_wise_qty[product_id]['pi_qty']
                    pi_foc_qty = po_item_wise_qty[product_id]['foc_qty']

                    bl_qty = bl_item_wise_qty[product_id]['qty']
                    bl_foc_qty = bl_item_wise_qty[product_id]['foc_qty']

                    if pi_qty != bl_qty:
                        bl.is_qty_not_matching = True
                        qty_mismatch_msg = "%s Qty Not Matching : %s," % (qty_mismatch_msg, self.env['product.product'].browse(product_id).name)

                    if pi_foc_qty != bl_foc_qty:
                        bl.is_qty_not_matching = True
                        qty_mismatch_msg = "%s Foc Qty Not Matching : %s," % (qty_mismatch_msg, self.env['product.product'].browse(product_id).name)

            if qty_mismatch_msg:
                bl.message_post(body=qty_mismatch_msg)


    def ready_to_enter_container_details(self):

        for rec in self:
            rec.state = 'container'

            if rec.po_type == 'import' and not rec.bl_entry_container_ids:
                raise ValidationError('Container number is missing')

            if rec.po_type == 'local':
                vals = {
                    'container_number': "Local Shipment %s" % rec.name,
                    'container_sequence': 1,
                    'bl_entry_id': rec.id
                }
                self.env['bl.entry.container'].create(vals)


            for po in rec.purchase_ids:
                for attachment in po.shipping_documents:
                    attachment.bl_id = rec.id


    def _compute_po_currency(self):
        for bl in self:
            currency_id = False
            for purchase in bl.purchase_ids:
                if purchase.currency_id:
                    currency_id = purchase.currency_id.id
            bl.currency_id = currency_id


    def _compute_total_price(self):
        for bl in self:
            total_price = 0
            for entry_line in bl.bl_entry_lines:
                total_price += entry_line.bl_total_price
            bl.total_price = total_price



    def send_documents_to_clearing_agent(self):

        self.ensure_one()
        ir_model_data = self.env['ir.model.data']

        template_id = ir_model_data._xmlid_lookup('kg_sarya_inventory.email_template_send_documents_to_clearing_agent_bl')[2]

        try:
            compose_form_id = ir_model_data._xmlid_lookup('mail.email_compose_message_wizard_form')[2]
        except ValueError:
            compose_form_id = False

        attachment_ids = []
        for doc in self.attachment_ids:
            for attachment in doc.doc_attachment_partner:
                attachment_ids.append(attachment.id)

        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'bl.entry',
            'active_model': 'bl.entry',
            'active_id': self.ids[0],
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'custom_layout': "mail.mail_notification_paynow",
            'force_email': True,
            'model_description' : 'Send Document to Clearing Agent',
            'default_attachment_ids': attachment_ids,
            'mark_clearing_document_sent': True,
        })


        lang = self.env.context.get('lang')
        self = self.with_context(lang=lang)


        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        if self.env.context.get('mark_clearing_document_sent'):
            self.write({'is_docs_send_to_agent': True})
        return super(BlEntry, self.with_context(
            mail_post_autofollow=self.env.context.get('mail_post_autofollow', True))).message_post(**kwargs)


    def _find_document_missing(self):
        for bl in self:
            document_missing = ""
            for atta in bl.attachment_ids:
                if atta.is_required and not atta.doc_attachment_partner:
                    document_missing = document_missing + " " + atta.document_name
                if atta.document_name.lower() == 'all' and atta.doc_attachment_partner:
                    document_missing = "All Documents Attached"
                    break

            if document_missing:
                if document_missing != 'All Documents Attached':
                    document_missing = "Document Missing: " + document_missing
            else:
                document_missing = "All Documents Attached"
            bl.document_missing = document_missing

    def action_view_bills(self):
        action = self.env.ref("account.action_move_in_invoice_type").sudo().read()[0]
        # remove default filters
        action["context"] = {}
        invoice_ids = self.invoice_ids

        if not invoice_ids:
            return True

        if len(invoice_ids) > 1:
            action["domain"] = [("id", "in", invoice_ids.ids)]
        elif invoice_ids:
            action["views"] = [(self.env.ref("account.view_move_form").id, "form")]
            action["res_id"] = invoice_ids.id

        return action

    @api.depends('shipment_advices.is_invoiced')
    def _find_pending_to_invoice(self):
        for rec in self:
            is_pending_to_invoice = False
            for advice in rec.shipment_advices:
                if advice.is_invoiced == 'not_invoiced' \
                        and advice.state in ['item_in_receiving', 'item_received', 'done']:
                    is_pending_to_invoice = True
            rec.is_pending_to_invoice = is_pending_to_invoice



    def generate_bill(self):
        #Generating Bills for all items received in a single bill
        for rec in self:
            pending_shipment_adv_ids = []
            for advice in rec.shipment_advices:
                if advice.is_invoiced == 'not_invoiced' \
                        and advice.state in ['item_in_receiving', 'item_received', 'done']:
                    pending_shipment_adv_ids.append(advice.id)

            if pending_shipment_adv_ids:
                shipment_advices = self.env['shipment.advice'].browse(pending_shipment_adv_ids)

                #1. Generating Bill
                shipment_advices.bill_create_invoice_per_bl(self)

                #2. Generating FOC
                shipment_advices.debit_note_for_foc_bl(self)

                #3. Generation Discount entry
                shipment_advices.additional_discount_entry(self)


    @api.depends('shipment_advices')
    def _compute_count(self):
        for rec in self:
            shipment_advice_count = len(rec.shipment_advices)
            rec.shipment_advice_count = shipment_advice_count


    def action_view_shipment_advice(self):
        action = self.env.ref("kg_sarya_inventory.shipment_advice_action").sudo().read()[0]
        # remove default filters
        action["context"] = {}
        shipment_advices = self.shipment_advices
        if len(shipment_advices) > 1:
            action["domain"] = [("id", "in", shipment_advices.ids)]
        elif shipment_advices:
            action["views"] = [(self.env.ref("kg_sarya_inventory.shipment_advice_form").id, "form")]
            action["res_id"] = shipment_advices.id
        return action


    @api.onchange('purchase_ids')
    def onchange_purchase_ids(self):
        for bl in self:
            vendor_id = False
            bl_number = ""
            po_type = ""

            container_type = ''
            container_volume = ''
            departure_date = False
            expected_date = False
            clearing_agent = False
            doc_clearing_agent = False

            for purchase_id in bl.purchase_ids:
                bl_number = purchase_id.bl_number
                vendor_id = purchase_id.partner_id.id
                po_type = purchase_id.po_type
                container_type = purchase_id.container_type
                container_volume = purchase_id.container_volume
                departure_date = purchase_id.estimated_departure_date
                expected_date = purchase_id.estimated_arrival_date

                clearing_agent = purchase_id.clearing_agent
                doc_clearing_agent = purchase_id.freight_forwarder



            bl.doc_clearing_agent = doc_clearing_agent
            bl.clearing_agent = clearing_agent


            bl.name = bl_number
            bl.vendor_id = vendor_id
            bl.po_type = po_type
            bl.container_type = container_type
            bl.container_volume = container_volume

            bl.departure_date = departure_date
            bl.expected_date = expected_date







    def _compute_number_of_container(self):
        for bl in self:
            number_of_container = len(bl.bl_entry_container_ids.ids)
            bl.number_of_container = number_of_container

    @api.onchange('bl_entry_container_ids')
    def onchange_containers(self):
        for bl in self:
            number_of_container = len(bl.bl_entry_container_ids.ids)
            bl.number_of_container = number_of_container


    def do_finance_approval(self):
        #check conditions
        for rec in self:
            rec.state = 'confirm'
            rec.gen_landed_cost_estimate()

            subject = 'BL is Approved %s %s' % (rec.vendor_id.name, rec.name)
            mail_content = " Hello,<br> BL %s is approved." % rec.name
            users = self.env.ref('kg_sarya_inventory.get_bl_approval_notification').users
            email_to = ""
            for usr in users:
                if usr.partner_id.email:
                    if not email_to:
                        email_to = usr.partner_id.email
                    else:
                        email_to = email_to + ', ' + usr.partner_id.email

            main_content = {
                'subject': _(subject),
                'author_id': self.env.user.partner_id.id,
                'body_html': mail_content,
                'email_to': email_to,
            }
            self.env['mail.mail'].sudo().create(main_content).send()






class BlEntry_Container(models.Model):
    _name = 'bl.entry.container'

    _rec_name = 'container_number'

    container_number = fields.Char("Container Number")
    container_sequence = fields.Integer("Seq")

    bl_entry_id = fields.Many2one('bl.entry', string='Bl Entry')

    bl_entry_lines = fields.One2many('bl.entry.lines', 'container_id', 'BL Lines')


class BlEntry_Lines(models.Model):
    _name = 'bl.entry.lines'

    _rec_name = 'bl_entry_id'

    bl_entry_id = fields.Many2one('bl.entry', string='Bl Entry')
    container_id = fields.Many2one('bl.entry.container', string='Container')

    currency_id = fields.Many2one('res.currency', string="Currency")

    product_id = fields.Many2one('product.product', string='Product', domain=[('purchase_ok', '=', True)], change_default=True)

    product_packaging_id = fields.Many2one('product.packaging', string='Packaging', domain="[('purchase', '=', True), ('product_id', '=', product_id)]")

    balance_po_qty = fields.Float("Balance PO Qty")

    po_qty = fields.Float("PO Qty")
    po_foc_qty = fields.Float("PO FOC Qty")


    lpo_price = fields.Monetary('LPO Price')

    fixed_discount_amount = fields.Monetary("Fixed Discount Amount")

    price_after_fixed_discount = fields.Monetary("Price After Fixed Discount")

    additional_discount = fields.Monetary("Additional Discount")


    bl_qty = fields.Float("BL Qty")

    bl_price = fields.Monetary("Unit Price")

    bl_total_price = fields.Monetary("BL Qty * Unit Price")

    qty_details = fields.One2many('bl.entry.lines.details', 'bl_entry_line_id', 'Qty Details')

    allowed_purchase_ids = fields.Many2many('purchase.order', 'bl_entry_line_allowed_purchase_order', "bl_entry_line_id", "allowed_purchase_id", copy=False)

    purchase_ids = fields.Many2many('purchase.order', 'bl_entry_line_purchase_order', "bl_entry_line_id", "purchase_id", copy=False, domain="[('id', 'in', allowed_purchase_ids)]")

    show_waring_msg = fields.Boolean("Show Warning Msg")

    is_price_not_matching = fields.Boolean("Is price not matching")
    is_qty_not_matching = fields.Boolean("Is Qty not matching")

    foc_qty = fields.Float("FOC Qty")


    @api.onchange("lpo_price", "bl_price")
    def get_fixed_discount_amount(self):

        for line in self:
            fixed_discount_amount = 0
            price_after_fixed_discount = 0
            suppiler_info = self.env['product.supplierinfo'].search([('partner_id', '=', line.bl_entry_id.vendor_id.id),
                                                    ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id)])

            if suppiler_info:
                disc1 = suppiler_info.discount_1
                disc2 = suppiler_info.discount_2
                total_discount = disc1 + disc2
                fixed_discount_amount = line.lpo_price * total_discount

            line.fixed_discount_amount = fixed_discount_amount

            line.price_after_fixed_discount = line.lpo_price - fixed_discount_amount

            line.additional_discount = line.price_after_fixed_discount - line.bl_price


    @api.onchange("purchase_ids")
    def onchange_purchase_ids(self):
        for line in self:
            show_waring_msg = True
            if line.purchase_ids:
                show_waring_msg = False
            line.show_waring_msg = show_waring_msg

    @api.onchange("product_id", "purchase_ids")
    def onchange_product(self):
        for line in self:

            if not line.product_id:
                line.product_packaging_id = False
                line.bl_price = 0
                line.qty_details = False

            #Find Purchase Packaging
            product_packaging_id = False
            lpo_price = 0
            currency_id = False
            po_qty = 0
            po_foc_qty = 0

            # if PO is selected on the line check packaging on that PO only
            if line.purchase_ids:
                for po in line.purchase_ids:
                    currency_id = po.currency_id.id
                    for po_line in po.order_line:
                        if po_line.product_id.id == line.product_id.id:
                            product_packaging_id = po_line.product_packaging_id.id
                            lpo_price = po_line.pkg_unit_price
                            po_qty += po_line.product_packaging_qty
                            po_foc_qty += po_line.pi_foc_qty
            else:
                for po in line.bl_entry_id.purchase_ids:
                    currency_id = po.currency_id.id
                    for po_line in po.order_line:
                        if po_line.product_id.id == line.product_id.id:
                            product_packaging_id = po_line.product_packaging_id.id
                            lpo_price = po_line.pkg_unit_price
                            po_qty += po_line.product_packaging_qty
                            po_foc_qty += po_line.pi_foc_qty

            line.product_packaging_id = product_packaging_id
            line.lpo_price = lpo_price
            line.currency_id = currency_id
            line.po_qty = po_qty
            line.po_foc_qty = po_foc_qty

    @api.onchange("bl_price", "qty_details")
    def onchange_bl_price_qty(self):
        for line in self:
            qty = 0
            foc_qty = 0
            for details in line.qty_details:
                qty += details.qty_to_receive
                foc_qty += details.foc_qty

            if qty > line.po_qty:
                for details in line.qty_details:
                    details.qty_to_receive = 0

                res = {}
                res['warning'] = {'title': _('Warning'),
                                  'message': _('You cannot input more than in LPO')}
                return res


            line.bl_qty = qty
            line.bl_total_price = qty * line.bl_price
            line.foc_qty = foc_qty








class BlEntry_Lines_Details(models.Model):
    _name = 'bl.entry.lines.details'

    bl_entry_line_id = fields.Many2one('bl.entry.lines', string='Bl Entry Line')

    expiry_date = fields.Date("Expiry Date")
    production_date = fields.Date(string="Production Date")
    qty_to_receive = fields.Float("Qty to Receive")
    foc_qty = fields.Float("FOC Qty")

    @api.onchange('expiry_date')
    def _get_expiration_date(self):
        for rec in self:
            rec.production_date = False
            if rec.expiry_date and rec.bl_entry_line_id.product_id.shelf_life:
                rec.production_date = rec.expiry_date - timedelta(days=rec.bl_entry_line_id.product_id.shelf_life)
            else:
                if not rec.bl_entry_line_id.product_id.shelf_life and rec.expiry_date:
                    rec.production_date = rec.expiry_date - timedelta(days=365)




class BlEntry_CostCustoms(models.Model):
    _name = 'bl.entry.cost.customs'

    _rec_name = 'product_id'

    bl_entry_id = fields.Many2one('bl.entry', string='Bl Entry')

    shipment_advice_id = fields.Many2one('shipment.advice', string='Shipment Advice')

    sa_landed_cost_id = fields.Many2one('shipment.advice.landed.cost', string='Shipment Advice Landed Cost')

    partner_id = fields.Many2one('res.partner', string="Vendor")
    container_id = fields.Many2one('bl.entry.container', string='Container')

    product_id = fields.Many2one('product.product', string="Item")

    account_id = fields.Many2one('account.account', 'Account', domain=[('deprecated', '=', False)])

    assess_amount = fields.Float('Assess Value')

    bcd_percent = fields.Float("BCD %")
    bcd_amount = fields.Float("BCD Amount")

    sws_percent = fields.Float("SWS %")
    sws_amount = fields.Float("SWS Amount")

    tax_ids = fields.Many2one('account.tax', string="VAT")

    total_amount_landed_cost = fields.Float("Total amount")

    vat_amount = fields.Float("Vat Amount")

    total_amount_with_vat = fields.Float("Total Amount with vat")

    @api.onchange('assess_amount', 'bcd_percent', 'sws_percent', 'tax_ids')
    def _onchange_amounts(self):

        for rec in self:
            assess_amount = rec.assess_amount
            bcd_percent = rec.bcd_percent
            bcd_amount = 0
            sws_percent = rec.sws_percent
            sws_amount = 0
            tax_ids = rec.tax_ids
            total_amount_landed_cost = 0
            vat_amount = 0
            total_amount_with_vat = 0

            if bcd_percent:
                bcd_amount = (assess_amount * bcd_percent)/100

            if sws_percent and bcd_amount:
                sws_amount = (bcd_amount * sws_percent)/100

            total_amount_landed_cost = bcd_amount + sws_amount

            if rec.tax_ids:
                vat_amount = (assess_amount + bcd_amount + sws_amount) * (tax_ids.amount / 100)
                total_amount_with_vat = bcd_amount + sws_amount + vat_amount



            rec.bcd_amount = bcd_amount
            rec.sws_amount = sws_amount
            rec.total_amount_landed_cost = total_amount_landed_cost
            rec.vat_amount = vat_amount
            rec.total_amount_with_vat = total_amount_with_vat










class BlEntry_Cost(models.Model):
    _name = 'bl.entry.cost'

    bl_entry_id = fields.Many2one('bl.entry', string='Bl Entry')
    partner_id = fields.Many2one('res.partner', string="Vendor")

    product_id = fields.Many2one('product.product', string="Cost")
    amount = fields.Float('Amount')
    tax_ids = fields.Many2one('account.tax', string="VAT")
    total_amount = fields.Float('Total')
    split_method = fields.Selection(SPLIT_METHOD,
                            string='Split Method',
                            required=True,
                            help="Equal : Cost will be equally divided.\n"
                                 "By Quantity : Cost will be divided according to product's quantity.\n"
                                 "By Current cost : Cost will be divided according to product's current cost.\n"
                                 "By Weight : Cost will be divided depending on its weight.\n"
                                 "By Volume : Cost will be divided depending on its volume.")
    account_id = fields.Many2one('account.account', 'Account', domain=[('deprecated', '=', False)])

    invoice_date = fields.Date('Commercial Invoice Date')
    inv_no = fields.Char(string='Invoice No.')

    type = fields.Selection([('actual', 'Actual'), ('estimation', 'Estimation')],
                            string="Cost Type",
                            default='actual',
                            required=True,
                            tracking=True,
                            copy=False)

    state = fields.Selection([('ready', 'Ready'), ('pending_approval', 'Pending Approval')],
                             string="Status",
                             default='ready')

    estimated_total_amount = fields.Float('Estimated Total')

    def approve_cost(self):

        for cost in self:
            cost.state = 'ready'
            msg = "Cost approved, Vendor: %s, Cost: %s, Amount: %s, Total: %s, Split Method: %s" % (
            cost.partner_id.name, cost.product_id.name, str(cost.amount), str(cost.total_amount), cost.split_method)
            cost.bl_entry_id.message_post(body=msg)




    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
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

    @api.model
    def create(self, vals):
        res = super(BlEntry_Cost, self).create(vals)
        for doc in res:
            msg = "Cost added, Vendor: %s, Cost: %s, Amount: %s, Total: %s, Split Method: %s" % (doc.partner_id.name, doc.product_id.name, str(doc.amount), str(doc.total_amount), doc.split_method)
            doc.bl_entry_id.message_post(body=msg)

        res.check_approval_is_required()
        res.estimation_notification()
        return res

    def estimation_notification(self):

        for cost in self:

            if not cost.bl_entry_id.expected_date:
                raise UserError(_('Please input ETA'))
            if not cost.bl_entry_id.departure_date:
                raise UserError(_('Please input ETD'))

            if cost.product_id.is_a_custom_duty and cost.type == 'estimation':

                bl_cost = 0
                purchase_currency = False
                for line in cost.bl_entry_id.bl_entry_lines:
                    bl_cost += line.bl_total_price
                    purchase_currency = line.currency_id

                currency_id = self.env.company.currency_id

                subject = 'BL Custom Duty Estimation %s' % cost.bl_entry_id.name
                mail_content = " Hello,<br>BL No : %s, " \
                               "Custom Invoice : %s, " \
                               "ETA : %s, " \
                               "ETD: %s, " \
                               "BL Value: %s %s " \
                               "and Custom Duty Estimation : %s %s" % (cost.bl_entry_id.name,
                                                                    cost.bl_entry_id.shipment_no,
                                                                    cost.bl_entry_id.expected_date.strftime("%d-%m-%Y"),
                                                                    cost.bl_entry_id.departure_date.strftime("%d-%m-%Y"),
                                                                    str(bl_cost), purchase_currency.name,
                                                                    str(cost.total_amount), currency_id.name)

                users = self.env.ref('kg_sarya_inventory.get_bl_cost_estimation_notification').users
                email_to = ""
                for usr in users:
                    if usr.partner_id.email:
                        if not email_to:
                            email_to = usr.partner_id.email
                        else:
                            email_to = email_to + ', ' + usr.partner_id.email

                main_content = {
                    'subject': _(subject),
                    'author_id': self.env.user.partner_id.id,
                    'body_html': mail_content,
                    'email_to': email_to,
                }
                self.env['mail.mail'].sudo().create(main_content).send()



    def write(self, values):
        for doc in self:
            msg = "Cost Edited, Vendor: %s, Cost: %s, Amount: %s, Total: %s, Split Method: %s, Edit Data: %s" % (doc.partner_id.name,
                              doc.product_id.name, str(doc.amount), str(doc.total_amount), doc.split_method, str(values))

            doc.bl_entry_id.message_post(body=msg)
        res = super(BlEntry_Cost, self).write(values)
        if 'total_amount' in values or 'amount' in values or 'type' in values:
            self.check_approval_is_required()
        return res

    def check_approval_is_required(self):
        '''For Custom duty check is it going above 1% more than the estimated cost'''
        for cost in self:

            if cost.product_id.is_a_custom_duty and cost.type == 'actual':

                bl_entry = cost.bl_entry_id

                estimated_custom_duty = bl_entry.computed_estimated_custom_duty()

                if estimated_custom_duty < 0.0001:
                    raise UserError(_('Estimated custom duty is coming zero, please check'))

                total_amount = cost.total_amount

                percentage_increase = ((total_amount - estimated_custom_duty) / estimated_custom_duty) * 100

                cost.estimated_total_amount = estimated_custom_duty

                if percentage_increase > 1:
                    cost.state = 'pending_approval'

                    currency_id = self.env.company.currency_id

                    subject = 'BL Custom Duty Variation Approval %s' % cost.bl_entry_id.name
                    mail_content = " Hello,<br>BL No : %s, " \
                                   "Custom Invoice : %s, " \
                                   "Estimated Custom Duty: %s %s " \
                                   "and Actual Cost : %s %s" % (cost.bl_entry_id.name,
                                                               cost.bl_entry_id.shipment_no,
                                                               str(estimated_custom_duty), currency_id.name,
                                                               str(cost.total_amount), currency_id.name)

                    users = self.env.ref('kg_sarya_inventory.get_bl_cost_variation_approval').users
                    email_to = ""
                    for usr in users:
                        if usr.partner_id.email:
                            if not email_to:
                                email_to = usr.partner_id.email
                            else:
                                email_to = email_to + ', ' + usr.partner_id.email

                    main_content = {
                        'subject': _(subject),
                        'author_id': self.env.user.partner_id.id,
                        'body_html': mail_content,
                        'email_to': email_to,
                    }
                    self.env['mail.mail'].sudo().create(main_content).send()

            if cost.product_id.is_a_freight_charge and cost.type == 'actual':
                bl_entry = cost.bl_entry_id

                clearing_agent = bl_entry.doc_clearing_agent
                from_port = False
                to_port = False

                for po in bl_entry.purchase_ids:
                    from_port = po.port_of_loading
                    to_port = po.port_of_discharge

                if not from_port:
                    raise UserError(_("Please check port of loading is configured in PO"))

                if not to_port:
                    raise UserError(_("Please check port of discharge is configured in PO"))

                estimation = self.env['fright.charge.estimation'].search([('vendor_id', '=', clearing_agent.id),
                                                                          ('from_port', '=', from_port.id),
                                                                          ('to_port', '=', to_port.id)], limit=1)

                if not estimation:
                    raise UserError(
                        _("Please contact Finance to configure fright estimation for %s, From Port : %s, To Port %s" % (
                        clearing_agent.name,
                        from_port.name, to_port.name)))


                freight_charge = self.env['product.product'].search([('is_a_freight_charge', '=', True)], limit=1)
                if not freight_charge:
                    raise UserError(_("Freight charge product is not configured"))

                accounts_data = freight_charge.product_tmpl_id.get_product_accounts()

                taxes = freight_charge.supplier_taxes_id.compute_all(
                    estimation.fright_charge * bl_entry.number_of_container,
                    currency=self.env.company.currency_id,
                    quantity=1.0
                )
                estimated_freight_charge = taxes.get('total_included')

                total_amount = cost.total_amount

                percentage_increase = ((total_amount - estimated_freight_charge) / estimated_freight_charge) * 100

                cost.estimated_total_amount = estimated_freight_charge

                if percentage_increase > estimation.price_variance_allowed:
                    cost.state = 'pending_approval'

                    currency_id = self.env.company.currency_id

                    subject = 'BL Freight Cost Variation Approval %s' % cost.bl_entry_id.name
                    mail_content = " Hello,<br>BL No : %s, " \
                                   "Custom Invoice : %s, " \
                                   "Estimated Freight Cost: %s %s " \
                                   "and Actual Cost : %s %s" % (cost.bl_entry_id.name,
                                                                cost.bl_entry_id.shipment_no,
                                                                str(estimated_freight_charge), currency_id.name,
                                                                str(cost.total_amount), currency_id.name)

                    users = self.env.ref('kg_sarya_inventory.get_bl_cost_variation_approval').users
                    email_to = ""
                    for usr in users:
                        if usr.partner_id.email:
                            if not email_to:
                                email_to = usr.partner_id.email
                            else:
                                email_to = email_to + ', ' + usr.partner_id.email

                    main_content = {
                        'subject': _(subject),
                        'author_id': self.env.user.partner_id.id,
                        'body_html': mail_content,
                        'email_to': email_to,
                    }
                    self.env['mail.mail'].sudo().create(main_content).send()



    def unlink(self):
        for doc in self:
            msg = "Cost Deleted, Vendor: %s, Cost: %s, Amount: %s, Total: %s, Split Method: %s" % (
            doc.partner_id.name, doc.product_id.name, str(doc.amount), str(doc.total_amount), doc.split_method)
            doc.bl_entry_id.message_post(body=msg)
        return super(BlEntry_Cost, self).unlink()


class Purchase(models.Model):
    _inherit = 'purchase.order'

    bl_id = fields.Many2one('bl.entry', string='BL Entry')
    bl_number = fields.Char("BL Number", tracking=True)




