# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.misc import get_lang
from odoo.addons import decimal_precision as dp
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta


# class Purchase_port_of_discharge(models.Model):
#     _name = 'purchase.port.of.discharge'
#
#     name = fields.Char("Place")




class Purchase(models.Model):
    _inherit = 'purchase.order'

    manual_exchange_rate = fields.Float(string='Exchange Rate')
    purchase_invoice = fields.Binary(string='Purchase Invoice')
    purchase_invoice_filename = fields.Char(string='File Name', store=True, copy=False)

    total_overdue_vendor = fields.Monetary(related="partner_id.total_overdue_vendor")
    total_overdue_vendor = fields.Monetary(compute='_compute_for_followup_vendor', string="Overdue Amount")

    mode_of_shipment = fields.Selection([('by_sea', 'By Sea'),
                                         ('by_air', 'By Air'),
                                         ('by_road', 'By Road')],
                                        string="Mode of Shipment")

    port_of_discharge = fields.Many2one('purchase.port.of.discharge', string="Port Of Discharge")

    port_of_loading = fields.Many2one('purchase.port.of.discharge', string="Port Of Loading")

    delivery_lead_time = fields.Integer("Lead Time (in Days)")



    estimated_arrival_date = fields.Date("ETA", tracking=True)

    estimated_departure_date = fields.Date("ETD", tracking=True)

    pi_entry_button_visibility = fields.Boolean(compute='compute_pi_entry_visibility')

    pi_updated_date = fields.Datetime("PI Updated On", tracking=True)

    finance_approval_date = fields.Date("Finance Approval Date", tracking=True)

    is_document_request_sent_to_vendors = fields.Boolean("Is document request sent to Vendors")

    last_document_reminder_sent_to_vendor = fields.Date("Last Document reminder sent to vendor")
    shipping_documents = fields.One2many('partner.attachments', 'purchase_order_id', string="Shipping Documents")

    is_finance_approval_required_for_rfq = fields.Boolean("Is finance approval required", compute='find_finance_approval_required')

    #It should be Freight Forwarder, by mistake it is updated as Clearing agent. To aviod data loss field text is renamed
    freight_forwarder = fields.Many2one('res.partner', string="Freight Forwarder")
    clearing_agent = fields.Many2one('res.partner', string="Clearing Agent")

    allowed_clearing_agents = fields.Many2many(string='Allowed Clearing Agents', related='partner_id.clearing_agents')

    date_approve_text = fields.Char("Date Approve Text", compute='get_date_approve_text')

    is_po_send_to_vendor = fields.Boolean("Is PO send to vendor?")

    due_date_based_on_bl = fields.Date("Due Date based on BL", compute='get_due_date_based_on_bl')

    def get_due_date_based_on_bl(self):
        for po in self:
            due_date_based_on_bl = False
            bl = self.env['bl.entry'].search([('purchase_ids', '=', po.id)], limit=1)
            if bl:
                boe_date = bl.boe_date
                if boe_date and po.payment_term_id:
                    invoice_payment_terms = po.payment_term_id._compute_terms(
                        date_ref=boe_date,
                        currency=po.currency_id,
                        tax_amount_currency=po.amount_tax,
                        tax_amount=po.amount_tax,
                        untaxed_amount_currency=po.amount_untaxed,
                        untaxed_amount=po.amount_untaxed,
                        company=po.company_id,
                        sign=1
                    )
                    for term_line in invoice_payment_terms['line_ids']:
                        due_date_based_on_bl = fields.Date.to_date(term_line.get('date'))
            po.due_date_based_on_bl = due_date_based_on_bl


    def send_po_to_vendor(self):
        '''
        This function opens a window to compose an email, with the edi purchase template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']

        if not self.partner_id.vendor_po_mail_template:
            raise UserError(_("Please select 'PO e-mail format' in vendor master"))

        template_id = self.partner_id.vendor_po_mail_template.id

        try:
            compose_form_id = ir_model_data._xmlid_lookup('mail.email_compose_message_wizard_form')[2]
        except ValueError:
            compose_form_id = False

        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'purchase.order',
            'active_model': 'purchase.order',
            'active_id': self.ids[0],
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'custom_layout': "mail.mail_notification_paynow",
            'force_email': True,
            'set_po_send_status_true': True,
        })

        lang = self.env.context.get('lang')
        if {'default_template_id', 'default_model', 'default_res_id'} <= ctx.keys():
            template = self.env['mail.template'].browse(ctx['default_template_id'])
            if template and template.lang:
                lang = template._render_lang([ctx['default_res_id']])[ctx['default_res_id']]

        self = self.with_context(lang=lang)
        ctx['model_description'] = _('Purchase Order')

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
        if self.env.context.get('set_po_send_status_true'):
            self.write({'is_po_send_to_vendor': True})
        return super(Purchase, self.with_context(
            mail_post_autofollow=self.env.context.get('mail_post_autofollow', True))).message_post(**kwargs)




    def get_date_approve_text(self):
        for po in self:
            date_approve_text = ""
            if po.date_approve:
                date_approve_text = po.date_approve.strftime('%d-%m-%Y')
            po.date_approve_text = date_approve_text


    def button_confirm_rfq(self):
        for po in self:

            if po.is_finance_approval_required_for_rfq and not po.finance_approval_date:
                raise UserError(_("You cannot directly confirm and please get fianace approval. Please click Save and send for finance approval"))

            po.button_approve()
            vendor_lead_time = po.partner_id.delivery_lead_time
            estimated_arrival_date = fields.Date.today() + relativedelta(days=vendor_lead_time)
            po.estimated_arrival_date = estimated_arrival_date
            po.update_shipping_document_list_from_vendor()
            po.finance_waiting_approval = ""

    def find_finance_approval_required(self):
        for rfq in self:
            approval_required = True
            if rfq.requisition_id:
                approval_required = False
            rfq.is_finance_approval_required_for_rfq = approval_required

    def update_shipping_doc_status(self):
        for po in self:
            is_shipping_documents_uploaded = True
            for doc in po.shipping_documents:
                if doc.is_required and not doc.doc_attachment_partner:
                    is_shipping_documents_uploaded = False
                if doc.doc_attachment_partner and doc.document_name.lower() == 'all':
                    is_shipping_documents_uploaded = True
                    break

            po.is_shipping_documents_uploaded = is_shipping_documents_uploaded


    def update_shipping_document_list_from_vendor(self):
        for po in self:
            is_shipping_documents_uploaded = True
            for doc in po.partner_id.shipping_documents:
                vals = {
                    'document_name': doc.name,
                    'is_required': doc.is_required,
                    'purchase_order_id': po.id
                }
                self.env['partner.attachments'].create(vals)
                if doc.is_required:
                    is_shipping_documents_uploaded = False

            #If there is no mandatory documents, mark it as shipping documents uploaded
            po.is_shipping_documents_uploaded = is_shipping_documents_uploaded



    @api.onchange('partner_id')
    def _onchange_partner_id_lead_time(self):
        for po in self:
            delivery_lead_time = po.partner_id.delivery_lead_time
            po.delivery_lead_time = delivery_lead_time

            # updating port of loading
            po.port_of_loading = po.partner_id.port_of_loading and po.partner_id.port_of_loading .id or False

            po.mode_of_shipment = po.partner_id.mode_of_shipment
            po.container_type = po.partner_id.container_type
            po.container_volume = po.partner_id.container_volume

            clearing_agent = False
            for c_agent in po.partner_id.clearing_agents:
                clearing_agent = c_agent.id
            po.clearing_agent = clearing_agent


    def button_approve_dummy(self):
        for po in self:
            vendor_lead_time = po.partner_id.delivery_lead_time
            estimated_arrival_date = fields.Date.today() + relativedelta(days=vendor_lead_time)
            po.estimated_arrival_date = estimated_arrival_date
            po.finance_waiting_approval = False


    def button_approve_purchase_order(self):
        for po in self:
            po.button_approve()
            vendor_lead_time = po.partner_id.delivery_lead_time
            estimated_arrival_date = fields.Date.today() + relativedelta(days=vendor_lead_time)
            po.estimated_arrival_date = estimated_arrival_date
            po.update_shipping_document_list_from_vendor()
            po.finance_waiting_approval = ""

            users = self.env.ref('cha_sarya_purchase.purchase_order_approval_notification').users
            email_to = ""
            for usr in users:
                if usr.partner_id.email:
                    if not email_to:
                        email_to = usr.partner_id.email
                    else:
                        email_to = email_to + ', ' + usr.partner_id.email

            main_content = {
                'subject': _('India: Purchase order %s is approved by Finance' % po.name),
                'author_id': self.env.user.partner_id.id,
                'body_html': 'Hi,<br>Purchase order %s is approved by Finance' % po.name,
                'email_to': email_to,
            }
            self.env['mail.mail'].sudo().create(main_content).send()



    def button_approve_pi_change(self):
        for po in self:
            po.finance_waiting_approval = False

            users = self.env.ref('cha_sarya_purchase.purchase_order_approval_notification').users
            email_to = ""
            for usr in users:
                if usr.partner_id.email:
                    if not email_to:
                        email_to = usr.partner_id.email
                    else:
                        email_to = email_to + ', ' + usr.partner_id.email

            main_content = {
                'subject': _('India: Purchase order %s is approved by Finance' % po.name),
                'author_id': self.env.user.partner_id.id,
                'body_html': 'Hi,<br>Purchase order %s is approved by Finance' % po.name,
                'email_to': email_to,
            }
            self.env['mail.mail'].sudo().create(main_content).send()

    def _send_email_to_vendors_for_documents(self):

        """Once ETD, BL number is updated 4 days after ETD date,
        system will send email automatically to suppliers requesting Shipping Docs.

        If it is not updated, system will send reminder email 15 days before set arrived date,
        following every 3 days until its updated CC relevant people."""

        po_to_exclude_on_remider = []
        #if ETA and ETD is very close, system will trigger two notfication.

        pending_date = fields.Date.today() - relativedelta(days=4)
        po_to_send_document = self.env['purchase.order'].search([('state', '=', 'purchase'),
                                                                 ('estimated_departure_date', '<', pending_date),
                                                                 ('bl_number', '!=', False),
                                                                 ('is_document_request_sent_to_vendors', '=', False)])

        for po in po_to_send_document:

            users = self.env.ref('cha_sarya_purchase.include_in_cc_of_mail_to_vendor').users
            email_cc = ""
            for usr in users:
                if usr.partner_id.email:
                    if not email_cc:
                        email_cc = usr.partner_id.email
                    else:
                        email_cc = email_cc + ', ' + usr.partner_id.email

            mail_template = po.partner_id.vendor_mail_template

            values = mail_template.generate_email(po.id, ['subject', 'body_html', 'email_from', 'email_to',
                                                            'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])
            values['email_to'] = po.partner_id.email
            values['email_cc'] = email_cc
            mail_mail_obj = self.env['mail.mail']

            msg_id = mail_mail_obj.create(values)
            mail_mail_obj.send(msg_id)

            po.is_document_request_sent_to_vendors = True
            po_to_exclude_on_remider.append(po.id)


        """15 days before set arrived date, following every 3 days until its updated CC relevant people."""

        po_to_send_reminder = self.env['purchase.order'].search([('state', '=', 'purchase'),
                                                                 ('is_document_request_sent_to_vendors', '=', True),
                                                                 ('is_shipping_documents_uploaded', '=', False),
                                                                 ('id', 'not in', po_to_exclude_on_remider)])

        for po in po_to_send_reminder:

            if not po.last_document_reminder_sent_to_vendor:
                """15 days before set arrived date"""

                estimated_arrival_date = po.estimated_arrival_date
                pending_date = fields.Date.today() + relativedelta(days=15)

                if estimated_arrival_date < pending_date:

                    po.last_document_reminder_sent_to_vendor = fields.Date.today()

                    users = self.env.ref('cha_sarya_purchase.include_in_cc_of_mail_to_vendor').users
                    email_cc = ""
                    for usr in users:
                        if usr.partner_id.email:
                            if not email_cc:
                                email_cc = usr.partner_id.email
                            else:
                                email_cc = email_cc + ', ' + usr.partner_id.email

                    mail_template = po.partner_id.vendor_mail_template

                    values = mail_template.generate_email(po.id, ['subject', 'body_html', 'email_from', 'email_to',
                                                                  'partner_to', 'email_cc', 'reply_to',
                                                                  'scheduled_date'])
                    values['email_to'] = po.partner_id.email
                    values['email_cc'] = email_cc
                    mail_mail_obj = self.env['mail.mail']

                    msg_id = mail_mail_obj.create(values)
                    mail_mail_obj.send(msg_id)

            else:

                """Following every 3 days until its updated CC relevant people"""

                last_document_reminder_sent_to_vendor = po.last_document_reminder_sent_to_vendor
                pending_date = fields.Date.today() - relativedelta(days=3)

                if last_document_reminder_sent_to_vendor <= pending_date:

                    po.last_document_reminder_sent_to_vendor = fields.Date.today()

                    users = self.env.ref('cha_sarya_purchase.include_in_cc_of_mail_to_vendor').users
                    email_cc = ""
                    for usr in users:
                        if usr.partner_id.email:
                            if not email_cc:
                                email_cc = usr.partner_id.email
                            else:
                                email_cc = email_cc + ', ' + usr.partner_id.email

                    mail_template = po.partner_id.vendor_mail_template

                    values = mail_template.generate_email(po.id, ['subject', 'body_html', 'email_from', 'email_to',
                                                                  'partner_to', 'email_cc', 'reply_to',
                                                                  'scheduled_date'])
                    values['email_to'] = po.partner_id.email
                    values['email_cc'] = email_cc
                    mail_mail_obj = self.env['mail.mail']

                    msg_id = mail_mail_obj.create(values)
                    mail_mail_obj.send(msg_id)


    def _send_email_to_to_update_bl(self):

        """Once ETD, BL number is updated 4 days after ETD date, This notification if BL not entered"""

        pending_date = fields.Date.today() - relativedelta(days=4)
        bl_pending_po = self.env['purchase.order'].search([('state', '=', 'purchase'),
                                                           ('estimated_departure_date', '<', pending_date),
                                                           ('bl_number', '=', False)])

        # Check BL is not entered after 4 Days
        if bl_pending_po:
            mail_content = "Hello,<br>List of PO without BL#"
            for po in bl_pending_po:
                mail_content = "%s<br>%s, Vendor : %s, Amount: %s" % (mail_content, po.name, po.partner_id.name, str(po.amount_total))

            users = self.env.ref('cha_sarya_purchase.notification_for_bl_not_entered_in_po').users
            email_to = ""
            for usr in users:
                if usr.partner_id.email:
                    if not email_to:
                        email_to = usr.partner_id.email
                    else:
                        email_to = email_to + ', ' + usr.partner_id.email

            main_content = {
                'subject': _('KSA: BL# not entered in PO'),
                'author_id': self.env.user.partner_id.id,
                'body_html': mail_content,
                'email_to': email_to,
            }
            self.env['mail.mail'].sudo().create(main_content).send()





    def email_purchase_order(self):
        '''
        This function opens a window to compose an email, with the edi purchase template message loaded by default
        '''

        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        Attachment = self.env['ir.attachment']

        mail_template = self.env.ref('cha_sarya_purchase.email_template_cha_sarya_po')
        values = mail_template.generate_email(self.id, ['subject', 'body_html', 'email_from', 'email_to', 'partner_to',
                                                        'email_cc', 'reply_to', 'scheduled_date'])
        values['email_to'] = self.partner_id.email
        mail_mail_obj = self.env['mail.mail']

        attachments = values.pop('attachments', [])
        attachment_ids = values.pop('attachment_ids', [])

        msg_id = mail_mail_obj.create(values)

        for attachment in attachments:
            attachment_data = {
                'name': attachment[0],
                'datas': attachment[1],
                'type': 'binary',
                'res_model': 'mail.message',
                'res_id': msg_id.mail_message_id.id,
            }
            attachment_ids.append((4, Attachment.create(attachment_data).id))
        if attachment_ids:
            msg_id.write({'attachment_ids': attachment_ids})
        mail_mail_obj.send(msg_id)

    def compute_pi_entry_visibility(self):
        for po in self:
            pi_entry_button_visibility = True
            if po.state not in ('done', 'purchase'):
                pi_entry_button_visibility = False
            if po.is_pi_qty_entered:
                pi_entry_button_visibility = False
            po.pi_entry_button_visibility = pi_entry_button_visibility

    def update_price_from_latest_contract(self):
        for po in self:
            msg = "Price Updated from latest Contract for following:"
            for line in po.order_line:
                old_price = line.pkg_unit_price
                line.sa_update_product_packaging_id()
                line.sa_update_pkg_unit_price()
                new_price = line.pkg_unit_price
                if old_price != new_price:
                    msg = "%s <br/> %s  ::  %s -> %s" % (msg, line.product_id.name, str(old_price), str(new_price))
            po.message_post(body=msg)

    def button_mark_pi_entry_completed(self):

        for po in self:
            if not po.purchase_invoice:
                raise UserError(_('Please upload PI on the PO'))

            change_in_qty = False
            for line in po.order_line:

                #Quantity is mached with below logic
                #PO Qty + PO FOC == PI QTY + PI FOC

                total_po_qty = line.approved_po_qty + line.foc_qty
                total_pi_qty = line.pi_qty + line.pi_foc_qty

                if total_po_qty != total_pi_qty:
                    change_in_qty = True

            if change_in_qty:
                po.finance_waiting_approval = "pi_change"
                po.send_notification_to_accounts_to_approve()

            po.is_pi_qty_entered = True
            po.pi_updated_date = fields.Datetime.now()

    def _compute_for_followup_vendor(self):
        today = fields.Date.context_today(self)
        for po in self:
            total_overdue_vendor = po.partner_id.total_overdue_vendor
            total_overdue_vendor = po.company_id.currency_id._convert(total_overdue_vendor, self.currency_id,
                                                                      po.company_id, today)
            po.total_overdue_vendor = total_overdue_vendor

    def button_sent_finance_approval(self):
        self.state = 'to approve'
        self.finance_waiting_approval = 'new_po'
        self.send_notification_to_accounts_to_approve()

    def _send_notification_for_pending_po(self):
        pending_po = self.env['purchase.order'].search([('state', '=', 'to approve')])
        mail_content = "Hello,<br>List of Pending for Approval"
        if pending_po:
            for po in pending_po:
                type = ""
                if po.finance_waiting_approval == 'new_po':
                    type = "RFQ"
                if po.finance_waiting_approval == 'pi_change':
                    type = "Value change on PI"
                mail_content = "%s<br>%s: %s, Vendor : %s, Amount: %s" % (
                mail_content, type, po.name, po.partner_id.name, str(po.amount_total))

            users = self.env.ref('cha_sarya_purchase.notification_for_pending_po_approval').users
            email_to = ""
            for usr in users:
                if usr.partner_id.email:
                    if not email_to:
                        email_to = usr.partner_id.email
                    else:
                        email_to = email_to + ', ' + usr.partner_id.email

            main_content = {
                'subject': _('India: RFQ/PI Pending for Approval'),
                'author_id': self.env.user.partner_id.id,
                'body_html': mail_content,
                'email_to': email_to,
            }
            self.env['mail.mail'].sudo().create(main_content).send()

    def send_notification_to_accounts_to_approve(self):

        type = ""
        if self.finance_waiting_approval == 'new_po':
            type = "RFQ"
        if self.finance_waiting_approval == 'pi_change':
            type = "Value change on PI"

        mail_content = "Hello,<br>Request for approval PO: %s, Vendor : %s, Amount: %s" % (
        self.name, self.partner_id.name, str(self.amount_total))

        users = self.env.ref('cha_sarya_purchase.notification_for_pending_po_approval').users
        email_to = ""
        for usr in users:
            if usr.partner_id.email:
                if not email_to:
                    email_to = usr.partner_id.email
                else:
                    email_to = email_to + ', ' + usr.partner_id.email

        main_content = {
            'subject': _('Purchase Orders to Approve : %s' % type),
            'author_id': self.env.user.partner_id.id,
            'body_html': mail_content,
            'email_to': email_to,
        }
        self.env['mail.mail'].sudo().create(main_content).send()

    def _send_notification_for_pending_pi(self):

        pi_pending_date = fields.Date.today() - relativedelta(days=4)
        pending_po_for_pi = self.env['purchase.order'].search([('pi_entry_button_visibility', '=', True),
                                                               ('date_approve', '<=', pi_pending_date)])
        if pending_po_for_pi:
            pending_po_for_pi.send_notification_to_update_pi_email()

    def send_notification_to_update_pi_email(self):

        mail_content = " Hello,<br>Please update PI for following purchase orders"
        for po in self:
            mail_content = "%s<br>PO: %s, Vendor : %s, Amount: %s" % (
            mail_content, po.name, po.partner_id.name, str(po.amount_total))

        users = self.env.ref('cha_sarya_purchase.notification_for_pending_pi_update').users
        email_to = ""
        for usr in users:
            if usr.partner_id.email:
                if not email_to:
                    email_to = usr.partner_id.email
                else:
                    email_to = email_to + ', ' + usr.partner_id.email

        main_content = {
            'subject': _('Pending Purchase Orders for PI to update'),
            'author_id': self.env.user.partner_id.id,
            'body_html': mail_content,
            'email_to': email_to,
        }
        self.env['mail.mail'].sudo().create(main_content).send()

    @api.onchange('currency_id')
    def _onchange_company(self):
        for po in self:
            manual_exchange_rate = 0
            if po.currency_id:
                date = fields.Date.today()
                company = po.company_id
                manual_exchange_rate = po.currency_id._get_rates(company, date)
                manual_exchange_rate = manual_exchange_rate[po.currency_id.id]
                # reverse rate calculation
                manual_exchange_rate = 1 / manual_exchange_rate
            po.manual_exchange_rate = manual_exchange_rate


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.depends('product_qty', 'product_uom', 'company_id')
    def _compute_price_unit_and_date_planned_and_name(self):
        """ Override original function to not calculate unit price from pricelist again"""
        for line in self:
            if not line.product_id or line.invoice_lines or not line.company_id:
                continue

            print("\n\n==_compute_price_unit_and_date_planned_and_name==\n\n")

            params = {'order_id': line.order_id}
            seller = line.product_id._select_seller(
                partner_id=line.partner_id,
                quantity=line.product_qty,
                date=line.order_id.date_order and line.order_id.date_order.date() or fields.Date.context_today(line),
                uom_id=line.product_uom,
                params=params)

            if seller or not line.date_planned:
                line.date_planned = line._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        return

    # Done as per jung request to manually enter the exchange rate in purchase order
    def _get_stock_move_price_unit(self):
        self.ensure_one()
        order = self.order_id
        price_unit = self.price_unit
        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
        if self.taxes_id:
            qty = self.product_qty or 1
            price_unit = self.taxes_id.with_context(round=False).compute_all(
                price_unit, currency=self.order_id.currency_id, quantity=qty, product=self.product_id,
                partner=self.order_id.partner_id
            )['total_void']
            price_unit = float_round(price_unit / qty, precision_digits=price_unit_prec)
        if self.product_uom.id != self.product_id.uom_id.id:
            price_unit *= self.product_uom.factor / self.product_id.uom_id.factor

        if order.currency_id != order.company_id.currency_id:
            if order.manual_exchange_rate > 0.0001 and False:
                price_unit = price_unit * order.manual_exchange_rate
            else:
                price_unit = order.currency_id._convert(
                    price_unit, order.company_id.currency_id, self.company_id,
                    self.date_order or fields.Date.today(), round=False)
        return price_unit

    @api.onchange('product_qty', 'product_uom')
    def _onchange_quantity(self):
        """ Override original function to not calculate unit price from pricelist again"""
        return


    def sa_update_product_packaging_id(self):
        if self.product_packaging_id:
            self.product_qty = self.product_packaging_id.qty * self.product_packaging_qty
            if self.product_id and self.product_packaging_id:
                vendor_pl = self.env['product.supplierinfo'].search([('product_tmpl_id','=',self.product_id.product_tmpl_id.id),('package_id','=',self.product_packaging_id.id)], limit=1)
                self.pkg_unit_price = vendor_pl.package_price

    @api.onchange('pkg_unit_price')
    def sa_update_pkg_unit_price(self):
        if self.pkg_unit_price and self.product_packaging_id:
            self.price_unit = self.pkg_unit_price/self.product_packaging_id.qty

    # @api.onchange('product_qty', 'product_uom')
    # def _onchange_quantity(self):
    #     print("\n\n*****************************************************************************")
    #     """ Override original function to not calculate unit price from pricelist again"""
    #     if not self.product_id:
    #         return
    #     params = {'order_id': self.order_id}
    #     seller = self.product_id._select_seller(
    #         partner_id=self.partner_id,
    #         quantity=self.product_qty,
    #         date=self.order_id.date_order and self.order_id.date_order.date(),
    #         uom_id=self.product_uom,
    #         params=params)
    #
    #     if seller or not self.date_planned:
    #         self.date_planned = self._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
    #
    #     # If not seller, use the standard price. It needs a proper currency conversion.
    #     if not seller:
    #         po_line_uom = self.product_uom or self.product_id.uom_po_id
    #         price_unit = self.env['account.tax']._fix_tax_included_price_company(
    #             self.product_id.uom_id._compute_price(self.product_id.standard_price, po_line_uom),
    #             self.product_id.supplier_taxes_id,
    #             self.taxes_id,
    #             self.company_id)
    #         if price_unit and self.order_id.currency_id and self.order_id.company_id.currency_id != self.order_id.currency_id:
    #             if self.order_id.manual_exchange_rate > 0.0001 and False:
    #                 price_unit = price_unit * self.order_id.manual_exchange_rate
    #             else:
    #                 price_unit = self.order_id.company_id.currency_id._convert(price_unit, self.order_id.currency_id,
    #                                                                            self.order_id.company_id,
    #                                                                            self.date_order or fields.Date.today())
    #         if not self.product_packaging_qty:
    #             self.price_unit = price_unit
    #         print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
    #         return
    #
    #     print("seller.price ==>> ", seller.price)
    #
    #     price_unit = self.env['account.tax']._fix_tax_included_price_company(seller.price,
    #                                                                          self.product_id.supplier_taxes_id,
    #                                                                          self.taxes_id,
    #                                                                          self.company_id) if seller else 0.0
    #
    #     if price_unit and seller and self.order_id.currency_id and seller.currency_id != self.order_id.currency_id:
    #         if self.order_id.manual_exchange_rate > 0.0001:
    #             price_unit = price_unit * self.order_id.manual_exchange_rate
    #         else:
    #             price_unit = seller.currency_id._convert(price_unit, self.order_id.currency_id,
    #                                                      self.order_id.company_id,
    #                                                      self.date_order or fields.Date.today())
    #
    #     #if seller and self.product_uom and seller.product_uom != self.product_uom:
    #     #    price_unit = seller.product_uom._compute_price(price_unit, self.product_uom)
    #
    #     if not self.product_packaging_qty:
    #         self.price_unit = price_unit
    #
    #     print("price_unit ==>> ", price_unit)
    #
    #     print("self.price_unit ==========>>> ", self.price_unit)
    #
    #     self._compute_amount()
    #
    #     print("\n\n#############################################################################")


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_price_unit(self):
        """ Returns the unit price for the move"""
        self.ensure_one()
        if self.purchase_line_id and self.product_id.id == self.purchase_line_id.product_id.id:
            price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
            line = self.purchase_line_id
            order = line.order_id
            price_unit = line.price_unit
            if line.taxes_id:
                qty = line.product_qty or 1
                price_unit = \
                line.taxes_id.with_context(round=False).compute_all(price_unit, currency=line.order_id.currency_id,
                                                                    quantity=qty)['total_void']
                price_unit = float_round(price_unit / qty, precision_digits=price_unit_prec)
            if line.product_uom.id != line.product_id.uom_id.id:
                price_unit *= line.product_uom.factor / line.product_id.uom_id.factor
            if order.currency_id != order.company_id.currency_id:

                if order.manual_exchange_rate > 0.0001 and False:
                    price_unit = price_unit * order.manual_exchange_rate
                else:
                    # The date must be today, and not the date of the move since the move move is still
                    # in assigned state. However, the move date is the scheduled date until move is
                    # done, then date of actual move processing. See:
                    # https://github.com/odoo/odoo/blob/2f789b6863407e63f90b3a2d4cc3be09815f7002/addons/stock/models/stock_move.py#L36
                    price_unit = order.currency_id._convert(
                        price_unit, order.company_id.currency_id, order.company_id, fields.Date.context_today(self),
                        round=False)
            return price_unit
        return super(StockMove, self)._get_price_unit()

