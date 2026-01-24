from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

from twilio.rest import Client
import json

class LocalPurchase(models.Model):
    _name = 'local.purchase'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Local Purchase'
    _order = 'id desc'


    def _default_pos_id(self):
        logged_user = self.env.user
        pos_id = False
        #Find mapped employee
        employee = self.env['hr.employee'].search([('user_id', '=', logged_user.id)])
        if employee:
            for emp in employee:
                pos = self.env['pos.config'].search(["|", ('basic_employee_ids', '=', emp.id),
                                                     ('advanced_employee_ids', '=', emp.id), ('terminal_type', '=', 'primary')], limit=1)
                if pos:
                    pos_id = pos.id
        return pos_id

    name = fields.Char(default='/')
    user_id = fields.Many2one(comodel_name='res.users', string='User', default=lambda self: self.env.user)
    state = fields.Selection(string='State',
        selection=[('new', 'New'),
                   ('manager', 'Pending Manager Approval'),
                   ('manager_approved', 'Manager Approved'),
                   ('procurement', 'Procurement Approval'),
                   ('finance', 'Finance Approved'),
                   ('confirm', 'Confirm'), ('cancel', 'Cancel') ], default='new', tracking=True)
    date = fields.Date(string='Date', default=fields.Date.today())
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company,
                                 readonly=True)
    line_ids = fields.One2many(comodel_name='local.purchase.line', inverse_name='local_purchase_id', string='Lines')
    requested = fields.Boolean('Requested', default=False, copy=False)
    vendor_id = fields.Many2one(comodel_name='res.partner', string='Vendor', required=True)
    move_id = fields.Many2one(comodel_name='account.move', string='Bill', readonly=True, copy=False)
    picking_id = fields.Many2one(comodel_name='stock.picking',  string='Goods Receipt Note', readonly=True, copy=False)
    pos_id = fields.Many2one(comodel_name='pos.config', string='POS Outlet', tracking=True, default=_default_pos_id)
    picking_type_id = fields.Many2one(comodel_name='stock.picking.type', string='Picking Type')
    currency_id = fields.Many2one( comodel_name='res.currency',  string='Currency', related='company_id.currency_id')
    total_untaxed = fields.Float(string='Total Untaxed', compute='_compute_total', tracking=True)
    total_tax = fields.Float(string='Total Tax', compute='_compute_total', tracking=True)
    total = fields.Float(string='Total', compute='_compute_total', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    grn_pending = fields.Boolean("GRN Pending",  compute='_find_grn_status', search="_search_grn_pending")
    invoice_pending = fields.Boolean("Invoice Pending",  compute='_find_invoice_status', search="_search_invoice_pending")
    ref = fields.Char(string='Bill Reference')
    purchase_type = fields.Selection(string='Purchase type',
        selection=[('normal', 'Normal'),
                   ('local_purchase', 'Local Purchase')],
        default='normal', tracking=True)

    payment_journal_id = fields.Many2one('account.journal', string="Payment Journal", tracking=True)
    landed_cost_ids = fields.One2many(comodel_name='landed.cost.line', inverse_name='local_purchase_id', string='Landed Costs')
    landed_cost = fields.Many2one(comodel_name='stock.landed.cost',  string='Landed Costs', readonly=True, copy=False)
    local_purchase_config_id = fields.Many2one('local.purchase.config', string="Purchase Configuration", required=True)
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position',
                                         domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    confirm_date = fields.Datetime(string='Confirmation Date', readonly=True, copy=False)
    send_by_email = fields.Boolean(string='Send by Email', default=True)

    # ********************
    # Smart Button
    # ********************

    picking_count = fields.Integer(compute="_compute_picking_count")
    bill_count = fields.Integer(compute="_compute_bill_count")

    @api.depends()
    def _compute_picking_count(self):
        for rec in self:
            rec.picking_count = self.env['stock.picking'].search_count([
                ('local_purchase_id', '=', rec.id)
            ])

    @api.depends()
    def _compute_bill_count(self):
        for rec in self:
            rec.bill_count = self.env['account.move'].search_count([
                ('local_purchase_id', '=', rec.id),
                ('move_type', '=', 'in_invoice')
            ])

    def action_view_pickings(self):
        return {
            'name': 'Related Pickings',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'domain': [('local_purchase_id', '=', self.id)],
        }

    def action_view_bills(self):
        return {
            'name': 'Vendor Bills',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [
                ('local_purchase_id', '=', self.id),
                ('move_type', '=', 'in_invoice')
            ],
        }
    # ********************
    # Smart Button End
    # ********************






    @api.constrains('ref')
    def _check_unique_nonzero_ref(self):
        for record in self:
            if record.ref:
                domain = [('ref', '=', record.ref)]
                if record.id:
                    domain.append(('id', '!=', record.id))
                dup = self.search_count(domain)
                if dup:
                    raise ValidationError("The Reference value must be unique and non-zero. This value already exists.")


    def print_receipt(self):
        if self.move_id:
            #return self.env.ref('account.report_invoice_with_payments').report_action(self.move_id)
            return self.env.ref('account.account_invoices').report_action(self.move_id)

    def send_notification(self, employee_ids, message, subject, button_url):
        for employee_id in employee_ids:
            # Email notification
            mail_content = "Dear " + str(employee_id.name)
            mail_content += "<br/><br/>" + message
            main_content = {
                "subject": subject,
                "body_html": mail_content,
                "email_to": employee_id.work_email,
            }
            self.env['mail.mail'].sudo().create(main_content).send()

            #Whatsapp message
            account_sid = self.env['ir.config_parameter'].sudo().get_param('twilio.account_sid', False)
            auth_token = self.env['ir.config_parameter'].sudo().get_param('twilio.auth_token', False)
            from_number = self.env['ir.config_parameter'].sudo().get_param('twilio.from', False)
            if employee_id.whatsapp_number:
                to_number = employee_id.whatsapp_number
            else:
                # Fallback to mobile or work phone if whatsapp number is not available
                to_number = employee_id.mobile_phone and employee_id.mobile_phone or employee_id.work_phone

            if account_sid and auth_token and from_number and to_number:
                from_number = "whatsapp:%s" % from_number
                to_number = to_number.replace(" ", '')
                to_number = "whatsapp:%s" % to_number
                content_variables = json.dumps({"1": message,
                                     "2": button_url})
                try:
                    client = Client(account_sid, auth_token)
                    tillow_message = client.messages.create(
                        from_=from_number,
                        content_sid='HXbecfa3982f02c410ede41a204763e958',
                        content_variables=content_variables,
                        to=to_number)
                except Exception:
                    pass


    @api.onchange('pos_id')
    def _onchange_pos_id(self):
        picking_type_id = False
        payment_journal_id = False
        if self.pos_id and self.pos_id.lpo_picking_type_id:
            picking_type_id = self.pos_id.lpo_picking_type_id.id
        self.picking_type_id = picking_type_id
        # --- Journal domain logic (new) ---
        if self.pos_id and self.pos_id.petty_cash_journal_id:
            payment_journal_id = self.pos_id.petty_cash_journal_id.id
        self.payment_journal_id = payment_journal_id

    @api.onchange('local_purchase_config_id')
    def _onchange_local_purchase_config_id(self):
        if self.local_purchase_config_id and self.local_purchase_config_id.operation_type_id:
            self.picking_type_id = self.local_purchase_config_id.operation_type_id.id

    @api.onchange('vendor_id', 'company_id')
    def onchange_vendor_id(self):
        if not self.vendor_id:
            self.fiscal_position_id = False
            self.purchase_type = 'normal'
        else:
            self.fiscal_position_id = self.env['account.fiscal.position']._get_fiscal_position(self.vendor_id)
            self.purchase_type = self.vendor_id.purchase_type or 'normal'

    def _find_grn_status(self):
        for po in self:
            grn_pending = False
            pickings = self.env['stock.picking'].search([('local_purchase_id', '=', po.id)])
            for picking in pickings:
                if picking.state not in ('done', 'cancel'):
                    grn_pending = True
            po.grn_pending = grn_pending

    def _search_grn_pending(self, operator, value):
        """Search for GRN pending based on related stock pickings"""
        if operator not in ('=', '!='):
            return []

        # Pending = there exists at least one picking linked via local_purchase_id not done/cancel
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [
                ('id', 'in', self.env['stock.picking'].search([
                    ('local_purchase_id', '!=', False),
                    ('state', 'not in', ['done', 'cancel'])
                ]).mapped('local_purchase_id').ids)
            ]

        # Not pending = either no picking or all pickings done/cancel
        elif (operator == '=' and not value) or (operator == '!=' and value):
            return [
                ('id', 'not in', self.env['stock.picking'].search([
                    ('local_purchase_id', '!=', False),
                    ('state', 'not in', ['done', 'cancel'])
                ]).mapped('local_purchase_id').ids)
            ]

        return []


    def _find_invoice_status(self):
        for po in self:
            invoice_pending = False
            for line in po.line_ids:
                if line.qty_received - line.qty_invoiced != 0:
                    invoice_pending = True
            po.invoice_pending = invoice_pending

    def _search_invoice_pending(self, operator, value):
        """Search for Invoice pending based on related stock pickings"""
        if operator not in ('=', '!='):
            return []

        # Find all POs with at least 1 line where qty_received != qty_invoiced
        po_lines = self.env['local.purchase.line'].search([('local_purchase_id.company_id', '=', self.env.company.id)])
        pending_po_ids = po_lines.filtered(
            lambda l: (l.qty_received - l.qty_invoiced) != 0
        ).mapped('local_purchase_id').ids

        # If searching invoice_pending = True
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [('id', 'in', pending_po_ids)]

        # invoice_pending = False
        if (operator == '=' and not value) or (operator == '!=' and value):
            return [('id', 'not in', pending_po_ids)]

        return []

    @api.depends('line_ids.qty', 'line_ids.unit_price', 'line_ids.tax_ids')
    def _compute_total(self):
        self.total_untaxed = sum(self.line_ids.mapped('total_untaxed'))
        self.total_tax = sum(self.line_ids.mapped('tax_amount'))
        self.total = sum(self.line_ids.mapped('total_untaxed')) + sum(self.line_ids.mapped('tax_amount'))

    @api.model
    def create(self, values):
        if self.env.company.company_type == 'retail':
            values['name'] = self.env['ir.sequence'].next_by_code('local.purchase.ret')
        if self.env.company.company_type == 'distribution':
            values['name'] = self.env['ir.sequence'].next_by_code('local.purchase.dist')
        return super(LocalPurchase, self).create(values)

    def unlink(self):
        if self.state != 'draft':
            raise ValidationError('Deleting the record only possible at DRAFT status.')
        return super(LocalPurchase, self).unlink()

    def notify_user(self, subject, body_html, users):
        email_to = ""
        for usr in users:
            if usr.partner_id.email:
                if not email_to:
                    email_to = usr.partner_id.email
                else:
                    email_to = email_to + ', ' + usr.partner_id.email

        main_content = {
            'subject': subject,
            'author_id': self.env.user.partner_id.id,
            'body_html': body_html,
            'email_to': email_to,
        }
        mail_obj = self.env['mail.mail']
        mail_obj.create(main_content).send()

    def action_request(self):

        #Check weather vendor mater is configured correctly
        for po in self:
            if not po.vendor_id.l10n_in_gst_treatment:
                msg = "GST Treatment for vendor is not configured in the system. Please contact finance"
                raise ValidationError(msg)

            if not po.vendor_id.property_supplier_payment_term_id:
                msg = "Payment Terms for the vendor is not configured in the system. Please contact finance"
                raise ValidationError(msg)

        self.requested = True
        self.state = 'manager'


        employee_ids = []
        lpo_approver_user_ids = self.env.company.lpo_approver_user_ids
        if self.pos_id:
            employees = self.pos_id.sudo().advanced_employee_ids
            if len(employees) == 0:
                raise UserError(_("Manager not mapped under Outlet configuration"))
            for employee in employees:
                employee_ids.append(employee.id)
        elif lpo_approver_user_ids:
            for user in lpo_approver_user_ids:
                if self.company_id.id in user.company_ids.ids:
                    employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
                    if employee:
                        employee_ids.append(employee.id)
                    elif False:
                        raise UserError(_("User %s does not have an employee record(MRP Config).") % user.name)
        else:
            group = "cha_sarya_purchase.can_approve_local_purchase_order"
            users = self.env.ref(group).users
            for user in users:
                if self.company_id.id in user.company_ids.ids:
                    employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
                    if employee:
                        employee_ids.append(employee.id)
                    elif False:
                        raise UserError(_("User %s does not have an employee record.") % user.name)
        if employee_ids:
            employees = self.env['hr.employee'].browse(employee_ids)
            for employee in employees:
                message = 'Hi %s, Purchase order %s waiting for Manager approval.' % (employee.name, self.name)
                subject = 'Local Purchase order %s Manager Approval Request' % self.name
                button_url = "#id=%s&cids=2&menu_id=697&action=876&model=local.purchase&view_type=form" % (str(self.id))
                self.send_notification(employees, message, subject, button_url)


    def action_manager_approve(self):
        #For local purchase manger approval is enough
        if self.purchase_type == 'local_purchase':
            self.action_confirm()
        else:
            self.state = 'manager_approved'
            self.action_confirm()
            self.confirm_date = fields.Datetime.now()
            # Send email if flag is set
            if self.send_by_email and self.vendor_id and self.vendor_id.email:
                template = self.env.ref('cha_sarya_purchase.email_template_local_purchase', raise_if_not_found=False)
                if template:
                    # Send email with report attached
                    template.send_mail(self.id, force_send=True)


            '''
            Finance approval is no more required for local purchase.
            '''
            # employee_ids = []
            # group = "cha_sarya_purchase.local_purchase_order_finance_approval"
            # users = self.env.ref(group).users
            # for user in users:
            #     if self.company_id.id in user.company_ids.ids:
            #         employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
            #         if employee:
            #             employee_ids.append(employee.id)
            #         elif False:
            #             raise UserError(_("User %s does not have an employee record.") % user.name)
            # if employee_ids:
            #     employees = self.env['hr.employee'].browse(employee_ids)
            #     for employee in employees:
            #         subject = 'Local Purchase order %s Finance Approval Request' % self.name
            #         message = 'Hi %s, Purchase order %s waiting for finance approval.' % (employee.name, self.name)
            #         button_url = "#id=%s&cids=2&menu_id=697&action=876&model=local.purchase&view_type=form" % (
            #             str(self.id))
            #         self.send_notification(employees, message, subject, button_url)


    def action_cancel(self):
        if self.move_id:
            self.move_id.button_draft()
        self.state = 'cancel'

    def reset_to_draft(self):
        self.state = 'new'

    def create_bill(self):
        print("lllllllllllllllllllllllllllllllllllllllll")
        print("lllllllllllllllllllllllllllllllllllllllll")
        print("lllllllllllllllllllllllllllllllllllllllll")
        print("lllllllllllllllllllllllllllllllllllllllll")
        print("lllllllllllllllllllllllllllllllllllllllll")
        # account_id = self.account_id or False
        acc_payable_id = self.vendor_id and self.vendor_id.property_account_payable_id or False
        local_purchase_journal_id = self.env.company.local_purchase_journal_id or False
        if not local_purchase_journal_id:
            raise UserError("Accounting configuration not done.\nKindly contact the administrator.")
        move_obj = self.env['account.move']
        analytic_account_id = False

        if self.local_purchase_config_id and self.local_purchase_config_id.analytic_account_id:
            analytic_account_id = self.local_purchase_config_id.analytic_account_id
        elif self.pos_id and self.pos_id.analytic_account_id:
            analytic_account_id = self.pos_id.analytic_account_id
        if analytic_account_id:
            analytic_distribution = {analytic_account_id.id: 100}
        # elif self.env.company.factory_analytic_account_id:
        #     analytic_distribution = {self.env.company.factory_analytic_account_id.id: 100}
        else:
            analytic_distribution = {}
        invoice_lines = []
        for purchase in self:
            if len(purchase.line_ids) == 0:
                raise UserError("No purchase lines!")
            if not purchase.vendor_id.l10n_in_gst_treatment:
                raise UserError("Please contact fiance to configure Gst treatment for the vendor!")
            for line in purchase.line_ids:
                total_qty = (line.qty_received - line.qty_invoiced) * line.packaging_id.qty
                if total_qty == 0:
                    continue
                # Recalculate unit price from total including GST
                unit_price_for_bill = line.total / total_qty
                invoice_lines.append((0, 0, {
                    'product_id': line.product_id and line.product_id.id or False,
                    'name': line.name,
                    'quantity': (line.qty_received - line.qty_invoiced) * line.packaging_id.qty,
                    'package_id': line.packaging_id.id,
                    'analytic_distribution' : analytic_distribution,
                    'product_packaging_qty': (line.qty_received - line.qty_invoiced),
                    'price_unit': unit_price_for_bill,#line.unit_price/line.packaging_id.qty,
                    'pkg_unit_price': unit_price_for_bill * line.packaging_id.qty,#line.unit_price,
                    'tax_ids': [],
                }))
            if purchase.landed_cost_ids:
                for landed_line in purchase.landed_cost_ids.filtered(lambda l: not l.is_billed):
                    invoice_lines.append((0, 0, {
                        'product_id': landed_line.product_id and landed_line.product_id.id or False,
                        'name': landed_line.product_id.display_name,
                        'price_unit': landed_line.price_unit,
                        'pkg_unit_price': landed_line.price_unit,
                        'tax_amount': landed_line.tax_amount,
                    }))
                    landed_line.is_billed = True
            print("invoice_lines", invoice_lines)
            if len(invoice_lines) == 0:
                raise UserError("No invoiceable lines found!")
            move_vals = {
                'partner_id': purchase.vendor_id.id,
                'invoice_date': purchase.date,
                'date': purchase.date,
                'journal_id': local_purchase_journal_id.id,
                'move_type': 'in_invoice',
                'ref': purchase.ref,
                'invoice_origin': purchase.name,
                'invoice_line_ids': invoice_lines,
                'l10n_in_gst_treatment': purchase.vendor_id.l10n_in_gst_treatment,
                'local_purchase_id': purchase.id,
            }
            move_id = move_obj.with_context(check_move_validity=False).create(move_vals)
            # move_id.with_context(check_move_validity=False)._recompute_dynamic_lines()
            move_id.sudo().action_post()
            # purchase.write({'move_id': move_id.id})

            if purchase.purchase_type == 'local_purchase':
                #Register payment for the invoice

                payment = self.env['account.payment.register'] \
                    .with_context(active_model='account.move', active_ids=move_id.ids) \
                    .create({'journal_id': purchase.payment_journal_id.id}) \
                    ._create_payments()
            # if self.pvr_request_id:
            #     self.pvr_request_id.state = 'completed'




    def create_picking(self):
        picking_type_id = self.picking_type_id
        if not picking_type_id:
            raise UserError(_("Picking type missing. Contact administrator."))
        location_dest_id = picking_type_id.default_location_dest_id
        location_id = self.env['stock.location'].search([('usage', '=', 'supplier')], limit=1)
        if not location_id:
            raise UserError(_("Cannot find supplier location, contact administrator."))
        picking_vals = {
            'picking_type_id': picking_type_id.id,
            'user_id': False,
            'date': fields.Datetime.now(),
            'origin': self.name,
            'location_dest_id': location_dest_id and location_dest_id.id,
            'location_id': location_id and location_id.id,
            'company_id': self.company_id.id,
            'local_purchase_id': self.id,
        }

        picking = self.env['stock.picking'].create(picking_vals)
        for line in self.line_ids:
            if line.unit_price == 0:
                raise UserError("Unit price cannot be zero \nKeep unit price .01 INR if item is FOC.")
            if line.qty > 0.001:
                move_vals = line.prepare_picking_line_int_transfer(picking, picking_type_id,
                                                                   location_id, location_dest_id,
                                                                   description=self.name)
                move = self.env['stock.move'].create(move_vals)
                line.stock_move_id = move.id
                # self.env['stock.move.line'].create(move_vals)
        picking.action_confirm()
        self.picking_id = picking.id

    def action_confirm(self):
        #self.create_bill()
        if self.picking_id:
            raise UserError("Goods Receipt Note already created.")
        self.create_picking()
        self.state = 'confirm'

        subject = _('Local Purchase order %s Approval Done' % self.name)
        body_html = 'Hi,<br> <br>Purchase order %s is fully approved.' % self.name
        user = self.create_uid
        employee_ids = []
        if self.company_id.id in user.company_ids.ids:
            employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
            if employee:
                employee_ids.append(employee.id)
            elif False:
                raise UserError(_("User %s does not have an employee record.") % user.name)
        if employee_ids:
            employees = self.env['hr.employee'].browse(employee_ids)
            # for employee in employees:
            subject = 'Local Purchase order %s Approval Done' % self.name
            message = 'Hi %s, Local Purchase order %s approval done.' % (employee.name, self.name)
            button_url = "#id=%s&cids=2&menu_id=697&action=876&model=local.purchase&view_type=form" % (
                str(self.id))
            self.send_notification(employees, message, subject, button_url)



    def action_create_advance_payment(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_account_payments")
        view_id = self.env.ref('account.view_account_payment_form').id
        action['views'] = [(view_id, 'form')]
        action['context'] = {
            'default_payment_type': 'outbound',
            'default_partner_type': 'supplier',
            'search_default_outbound_filter': 1,
            'default_move_journal_types': ('bank', 'cash'),
            'display_account_trust': True,
            'default_partner_id': self.vendor_id.id,
            'default_amount': self.total,
        }
        return action

    def cron_check_grn_pending(self):
        """Send GRN pending notifications if confirm_date > 5 days"""
        five_days_ago = fields.Datetime.now() - timedelta(days=5)
        records = self.search([
            ('grn_pending', '=', True),
            ('confirm_date', '<=', five_days_ago),
            ('pos_id', '!=', False)
        ])
        print("records", records, ">>>>>>>>>>>>>>>>>>>>>>")
        for rec in records:
            users = rec.pos_id.sudo().advanced_employee_ids
            if not users:
                continue

            message = (
                f"⚠️ GRN Pending Alert:\n\n"
                f"Purchase `{rec.name}` is pending GRN for more than 5 days.\n"
                f"Confirm Date: {rec.confirm_date.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            # Create Email notifications
            template = self.env.ref('cha_sarya_purchase.email_template_grn_pending', raise_if_not_found=False)
            if template:
                template.send_mail(rec.id, force_send=True)



class LocalPurchaseLines(models.Model):
    _name = 'local.purchase.line'
    _description = 'Local Purchase Lines'

    name = fields.Char(string='Description', required=True)
    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    packaging_id = fields.Many2one(comodel_name='product.packaging', string='Packaging',
        domain="[('purchase', '=', True), ('product_id', '=', product_id)]")
    qty = fields.Float(string='Qty Ordered')
    qty_received = fields.Float(string='Qty Received', compute='_compute_qty_received')
    qty_invoiced = fields.Float(string='Qty Invoiced', compute='_compute_qty_invoiced')
    unit_price = fields.Float(string='Unit Price')
    tax_amount = fields.Float(string='Tax Amount', compute='_compute_total')
    total_untaxed = fields.Float(string='Total Untaxed', compute='_compute_total')
    total = fields.Float(string='Total', compute='_compute_total')
    local_purchase_id = fields.Many2one(comodel_name='local.purchase', string='Local Purchase', required=False)
    tax_ids = fields.Many2many(comodel_name='account.tax', string='Taxes')
    stock_move_id = fields.Many2one(comodel_name='stock.move', string='Stock Move')

    @api.onchange('unit_price')
    def onchange_unit_price(self):
        if self.unit_price > 0:
            if self.user_has_groups('cha_sarya_purchase.can_override_lpo_prices'):
                return {}
            if self.packaging_id and self.product_id:
                vendor = self.local_purchase_id.vendor_id
                pre_unit_price = 0
                for seller_id in self.product_id.seller_ids:
                    if seller_id.partner_id.id == vendor.id and \
                            seller_id.package_id.id == self.packaging_id.id:
                        pre_unit_price = seller_id.package_price
                if pre_unit_price > 0:
                    lower_bound = pre_unit_price * 0.80
                    upper_bound = pre_unit_price * 1.20
                    if lower_bound <= self.unit_price <= upper_bound:
                        print("unit_price is within ±20% of pre_unit_price.")
                    else:
                        self.unit_price = pre_unit_price
                        print("unit_price is outside the ±20% range of pre_unit_price.")
                        res = {}
                        res['warning'] = {'title': _('Warning'),
                                          'message': _('you cannot input purchase cost more or less than 20% price master')}
                        return res


    @api.onchange('packaging_id')
    def onchange_packaging_on_line(self):
        unit_price = 0
        if self.packaging_id and self.product_id:
            vendor = self.local_purchase_id.vendor_id
            for seller_id in self.product_id.seller_ids:
                if seller_id.partner_id.id == vendor.id and\
                    seller_id.package_id.id == self.packaging_id.id:
                    unit_price = seller_id.package_price
        self.unit_price = unit_price

    def _compute_qty_received(self):
        for rec in self:
            local_purchase_id = rec.local_purchase_id
            qty_received = 0
            picking_ids = self.env['stock.picking'].search(
                [('local_purchase_id', '=', local_purchase_id.id), ('state', '=', 'done')])
            if picking_ids:
                for picking_id in picking_ids:
                    print(picking_id, "  ====  ")
                    print(picking_id.state, "  ====  ")
                    for move in picking_id.move_ids_without_package:
                        print("move", move.state, "  ====  ")
                        if move.state == 'done' and move.product_id.id == rec.product_id.id:
                            qty_received += move.quantity
            if qty_received > 0:
                qty_received = qty_received/rec.packaging_id.qty
            rec.qty_received = qty_received

    def _compute_qty_invoiced(self):
        for rec in self:
            local_purchase_id = rec.local_purchase_id
            qty_invoiced = 0
            bills = self.env['account.move'].search([('local_purchase_id', '=', local_purchase_id.id),
                                                     ('move_type', '=', 'in_invoice'),
                                                     ('state', '=', 'posted')])
            if local_purchase_id.picking_id:
                for bill in bills:
                    for line in bill.invoice_line_ids:
                        if bill.state == 'posted' and line.product_id.id == rec.product_id.id:
                            qty_invoiced += line.product_packaging_qty
            rec.qty_invoiced = qty_invoiced



    @api.depends('qty', 'unit_price', 'tax_ids')
    def _compute_total(self):
        for rec in self:
            tax_results = self.env['account.tax']._compute_taxes([rec._convert_to_tax_base_line_dict()])
            totals = next(iter(tax_results['totals'].values()))
            rec.tax_amount = totals['amount_tax']
            rec.total_untaxed = rec.qty * rec.unit_price
            rec.total = (rec.qty * rec.unit_price) + rec.tax_amount

    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.local_purchase_id.vendor_id,
            currency=self.local_purchase_id.currency_id,
            product=self.product_id,
            taxes=self.tax_ids,
            price_unit=self.unit_price,
            quantity=self.qty,
            discount=0, #self.discount,
            price_subtotal=self.qty * self.unit_price, #self.price_subtotal,
        )

    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            self.name = self.product_id.name

            primary_packaging_id = self.env['product.packaging'].search(
                [('product_id', '=', self.product_id.id), ('primary_unit', '=', True)])

            if not primary_packaging_id:
                raise ValidationError('Primary packaging is missing')

            if len(primary_packaging_id) > 1:
                raise ValidationError('You cannot make 2 packaging simultaneosly as primary packaging. Please contact procurment team')

            tax_ids = False
            if self.product_id.supplier_taxes_id:
                tax_ids = self.product_id.supplier_taxes_id.ids
            # self.tax_ids = tax_ids
            self._compute_tax_id()

        else:
            self.name = False
            self.packaging_id = False
            self.tax_ids = False

    def _compute_tax_id(self):
        for line in self:
            line = line.with_company(line.local_purchase_id.company_id)
            fpos = line.local_purchase_id.fiscal_position_id or line.local_purchase_id.fiscal_position_id._get_fiscal_position(line.local_purchase_id.vendor_id)
            # filter taxes by company
            taxes = line.product_id.supplier_taxes_id.filtered_domain(self.env['account.tax']._check_company_domain(line.local_purchase_id.company_id))
            line.tax_ids = fpos.map_tax(taxes)

    def prepare_picking_line_int_transfer(self, picking, picking_type_id,
                                          location_id, location_dest_id, description=''):
        self.ensure_one()
        vals = []
        # Finding qty against each lot received for same product
        product_uom_qty = self.qty * self.packaging_id.qty
        product_uom = self.product_id.uom_id

        total_qty = self.qty * self.packaging_id.qty
        # Recalculate unit price from total including GST
        unit_price_per_qty = self.total / total_qty

        price_unit = self.unit_price/self.packaging_id.qty

        vals.append({
            'product_id': self.product_id.id,
            'date': fields.Datetime.now(),
            'location_id': location_id and location_id.id,
            'location_dest_id': location_dest_id and location_dest_id.id,
            'picking_id': picking.id,
            'company_id': self.local_purchase_id.company_id.id,
            'origin': description,
            'name': self.product_id.name,
            'price_unit': unit_price_per_qty,
            'quantity': product_uom_qty,
            'product_uom_qty': product_uom_qty,
            'product_uom': product_uom.id,
        })
        return vals

class StockDelivery(models.Model):
    _inherit = 'stock.picking'

    local_purchase_id = fields.Many2one(comodel_name='local.purchase', string='Local Purchase')

    def button_validate(self):
        res = super(StockDelivery, self).button_validate()
        local_lpo = False
        if self.local_purchase_id:
            local_lpo = self.local_purchase_id
        for picking in self:
            if local_lpo and local_lpo.landed_cost_ids.filtered(lambda l: not l.is_billed):
                if picking.picking_type_id.code == "incoming":
                    landed_cost = self.env["stock.landed.cost"].create({
                        "picking_ids": [(6, 0, [picking.id])],
                        "state": "draft",
                    })
                    landed_cost_lines = []
                    for line in local_lpo.landed_cost_ids.filtered(lambda l: not l.is_billed):
                        landed_cost_lines.append(({
                            'product_id': line.product_id and line.product_id.id or False,
                            'price_unit': line.total,
                            'cost_id': landed_cost.id,
                            'split_method': 'by_current_cost_price',
                            'name': line.product_id.display_name,
                            'account_id': (
                                    line.product_id.property_account_expense_id.id
                                    or line.product_id.categ_id.property_account_expense_categ_id.id
                            ),
                        }))
                    if landed_cost_lines:
                        self.env["stock.landed.cost.lines"].create(landed_cost_lines)
                    landed_cost.compute_landed_cost()
                    employee_ids = []
                    group = "cha_sarya_purchase.can_approve_local_purchase_order"
                    users = self.env.ref(group).users
                    for user in users:
                        if local_lpo.company_id.id in user.company_ids.ids:
                            employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
                            if employee:
                                employee_ids.append(employee.id)
                            else:
                                raise UserError(_("User %s does not have an employee record.") % user.name)
                    if employee_ids:
                        employees = self.env['hr.employee'].browse(employee_ids)
                        for employee in employees:
                            subject = 'Landed Cost %s Finance Validate Request' % landed_cost.name
                            message = 'Hi %s, <br/><br/>Landed Cost %s waiting for finance approval.' % (
                                employee.name, landed_cost.name)
                            button_url = "#id=%s&cids=2&menu_id=697&action=876&model=stock.landed.cost&view_type=form" % (
                                str(landed_cost.id))
                            try:
                                self.send_notification(employees, message, subject, button_url)
                            except Exception:
                                _logger.error("Failed to send notification for landed cost approval.")
                    local_lpo.landed_cost = landed_cost.id
                    landed_cost.button_validate()
        return res


class LandedCostLine(models.Model):
    _name = 'landed.cost.line'

    local_purchase_id = fields.Many2one(comodel_name='local.purchase', string='Local Purchase', required=False)
    product_id = fields.Many2one(comodel_name='product.product', string='Product', domain=[('landed_cost_ok', '=', True)])
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency', related='local_purchase_id.currency_id')
    price_unit = fields.Monetary(string='Cost', currency_field='currency_id')
    tax_amount = fields.Float(string='Tax Amount', compute='_compute_total')
    total_untaxed = fields.Float(string='Total Untaxed', compute='_compute_total')
    total = fields.Float(string='Total', compute='_compute_total')
    tax_ids = fields.Many2many(comodel_name='account.tax', string='Taxes')
    is_billed = fields.Boolean(string='Is Billed', default=False)

    @api.depends('price_unit', 'tax_ids')
    def _compute_total(self):
        for rec in self:
            tax_results = self.env['account.tax']._compute_taxes([rec._convert_to_tax_base_line_dict()])
            totals = next(iter(tax_results['totals'].values()))
            rec.tax_amount = totals['amount_tax']
            rec.total_untaxed = 1 * rec.price_unit
            rec.total = (1 * rec.price_unit) + rec.tax_amount

    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.local_purchase_id.vendor_id,
            currency=self.local_purchase_id.currency_id,
            product=self.product_id,
            taxes=self.tax_ids,
            price_unit=self.price_unit,
            quantity=1,
            discount=0, #self.discount,
            price_subtotal=1 * self.price_unit, #self.price_subtotal,
        )

    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            # self.name = self.product_id.name
            #
            # primary_packaging_id = self.env['product.packaging'].search(
            #     [('product_id', '=', self.product_id.id), ('primary_unit', '=', True)])
            #
            # if not primary_packaging_id:
            #     raise ValidationError('Primary packaging is missing')
            #
            # if len(primary_packaging_id) > 1:
            #     raise ValidationError('You cannot make 2 packaging simultaneosly as primary packaging. Please contact procurment team')

            tax_ids = False
            if self.product_id.supplier_taxes_id:
                tax_ids = self.product_id.supplier_taxes_id.ids
            self.tax_ids = tax_ids

        else:
            # self.name = False
            # self.packaging_id = False
            self.tax_ids = False



class AccountMove(models.Model):
    _inherit = 'account.move'

    local_purchase_id = fields.Many2one(comodel_name='local.purchase', string='Local Purchase')
