from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError

class OfficePurchase(models.Model):
    _name = 'office.purchase'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Office Purchase'
    _order = 'id desc'

    name = fields.Char(default='/')
    user_id = fields.Many2one(comodel_name='res.users', string='User', default=lambda self: self.env.user)
    state = fields.Selection(string='State',
        selection=[('new', 'New'),
                   ('finance', 'Pending Finance Approval'),
                   ('finance_approved', 'Finance Approved'),
                   # ('confirm', 'Pending Bill Creation'),
                   ('done', 'Done'),
                   ('cancel', 'Cancelled') ], default='new', tracking=True)
    date = fields.Date(string='Date', default=fields.Date.today())
    invoice_date = fields.Date(string='Invoice Date')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company,
                                 readonly=True)
    line_ids = fields.One2many(comodel_name='office.purchase.line', inverse_name='office_purchase_id', string='Lines')
    requested = fields.Boolean('Requested', default=False, copy=False)
    vendor_id = fields.Many2one(comodel_name='res.partner', string='Vendor', required=True)
    move_id = fields.Many2one(comodel_name='account.move', string='Bill', readonly=True, copy=False)
    picking_type_id = fields.Many2one(comodel_name='stock.picking.type', string='Picking Type')
    currency_id = fields.Many2one( comodel_name='res.currency',  string='Currency', related='company_id.currency_id')
    total_untaxed = fields.Float(string='Total Untaxed', compute='_compute_total', tracking=True)
    total_tax = fields.Float(string='Total Tax', compute='_compute_total', tracking=True)
    total = fields.Float(string='Total', compute='_compute_total', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    ref = fields.Char(string='Invoice Reference')

    payment_journal_id = fields.Many2one('account.journal', string="Payment Journal", tracking=True)
    opo_attach_id = fields.Many2many('ir.attachment', 'opo_attach_rel', 'doc_id_office', 'attach_id_office', string="Attachment",
                                     copy=False)

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

    @api.depends('line_ids.qty', 'line_ids.unit_price', 'line_ids.tax_ids')
    def _compute_total(self):
        self.total_untaxed = sum(self.line_ids.mapped('total_untaxed'))
        self.total_tax = sum(self.line_ids.mapped('tax_amount'))
        self.total = sum(self.line_ids.mapped('total_untaxed')) + sum(self.line_ids.mapped('tax_amount'))

    @api.model
    def create(self, values):
        res = super().create(values)
        print('self.env', self.env['ir.sequence'].next_by_code('office.purchase'))
        res.name = self.env['ir.sequence'].next_by_code('office.purchase')
        return res

    def send_notification(self, employee_ids, message, subject, button_url):
        for employee_id in employee_ids:
            # Email notification
            main_content = {
                "subject": subject,
                "body_html": message,
                "email_to": employee_id.work_email,
            }
            self.env['mail.mail'].sudo().create(main_content).send()

    def action_request(self):
        if not self.opo_attach_id:
            raise UserError(_("Please Add the Invoice Attachment"))
        for line in self.line_ids:
            if line.unit_price <= 0:
                raise UserError(_("Please Add the Product Price"))
            if line.qty_received <= 0:
                raise UserError(_("Please add Received quantity"))
        self.requested = True
        self.state = 'finance'
        employee_ids = []
        group = "cha_sarya_purchase.can_approve_office_purchase_order"
        users = self.env.ref(group).users
        print('users', users)
        for user in users:
            if self.company_id.id in user.company_ids.ids:
                employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
                if employee:
                    employee_ids.append(employee.id)
                else:
                    raise UserError(_("User %s does not have an employee record.") % user.name)
        if employee_ids:
            employees = self.env['hr.employee'].browse(employee_ids)
            for employee in employees:
                subject = 'Office Purchase order %s Finance Approval Request' % self.name
                message = 'Hi %s, <br/><br/>Purchase order %s waiting for finance approval.' % (employee.name, self.name)
                button_url = "#id=%s&cids=2&menu_id=697&action=876&model=office.purchase&view_type=form" % (
                    str(self.id))
                self.send_notification(employees, message, subject, button_url)

    def action_finance_approve(self):
        self.state = 'finance_approved'
        user = self.create_uid
        if self.company_id.id in user.company_ids.ids:
            employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
            if employee:
                subject = 'Office Purchase order %s Approval Done' % self.name
                message = 'Hi %s,<br/><br/>Office Purchase order %s approval done.' % (employee.name, self.name)
                button_url = "#id=%s&cids=2&menu_id=697&action=876&model=office.purchase&view_type=form" % (
                    str(self.id))
                self.send_notification(employee, message, subject, button_url)
            else:
                raise UserError(_("User %s does not have an employee record.") % user.name)

    # def action_confirm(self):
    #     for line in self.line_ids:
    #         if line.qty_received <= 0:
    #             raise UserError(_("Please add Received quantity"))
    #     self.state = 'confirm'

    def create_bill(self):
        acc_payable_id = self.vendor_id and self.vendor_id.property_account_payable_id or False
        local_purchase_journal_id = self.env.company.local_purchase_journal_id or False
        if not local_purchase_journal_id:
            raise UserError("Accounting configuration not done.\nKindly contact the administrator.")
        move_obj = self.env['account.move']
        if self.env.company.office_analytic_account_id:
            analytic_distribution = {self.env.company.office_analytic_account_id.id: 100}
        else:
            analytic_distribution = {}
        invoice_lines = []
        for purchase in self:
            if len(purchase.line_ids) == 0:
                raise UserError("No purchase lines!")
            if not purchase.vendor_id.l10n_in_gst_treatment:
                raise UserError("Please contact fiance to configure Gst treatment for the vendor!")
            for line in purchase.line_ids:
                invoice_lines.append((0, 0, {
                    'product_id': line.product_id and line.product_id.id or False,
                    'name': line.name,
                    'quantity': line.qty_received,
                    'package_id': line.packaging_id.id,
                    'analytic_distribution' : analytic_distribution,
                    'price_unit': line.unit_price,
                    'tax_ids': line.tax_ids.ids,
                }))
            move_vals = {
                'partner_id': purchase.vendor_id.id,
                'invoice_date': purchase.date,
                'date': purchase.date,
                'journal_id': local_purchase_journal_id.id,
                'move_type': 'in_invoice',
                'ref': purchase.ref,
                'invoice_origin': purchase.name,
                'invoice_line_ids': invoice_lines,
                'l10n_in_gst_treatment': purchase.vendor_id.l10n_in_gst_treatment
            }
            move_id = move_obj.with_context(check_move_validity=False).create(move_vals)
            move_id.action_post()
            purchase.write({'move_id': move_id.id, 'invoice_date': fields.Date.today()})
            for line in self.line_ids:
                line.billed_quantity = line.qty_received
            self.state = 'done'

    def action_cancel(self):
        self.state = 'cancel'

    def reset_to_draft(self):
        self.state = 'new'


class OfficePurchaseLines(models.Model):
    _name = 'office.purchase.line'
    _description = 'Office Purchase Lines'

    name = fields.Char(string='Description', required=True)
    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    packaging_id = fields.Many2one(comodel_name='product.packaging', string='Packaging',
        domain="[('purchase', '=', True), ('product_id', '=', product_id)]")
    qty = fields.Float(string='Qty Ordered')
    qty_received = fields.Float(string='Qty Received')
    billed_quantity = fields.Float(string='Billed Quantity')
    unit_price = fields.Float(string='Unit Price')
    tax_amount = fields.Float(string='Tax Amount', compute='_compute_total')
    total_untaxed = fields.Float(string='Total Untaxed', compute='_compute_total')
    total = fields.Float(string='Total', compute='_compute_total')
    office_purchase_id = fields.Many2one(comodel_name='office.purchase', string='Office Purchase', required=False)
    tax_ids = fields.Many2many(comodel_name='account.tax', string='Taxes')

    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            self.name = self.product_id.name

            tax_ids = False
            if self.product_id.supplier_taxes_id:
                tax_ids = self.product_id.supplier_taxes_id.ids
            self.tax_ids = tax_ids

        else:
            self.name = False
            self.packaging_id = False
            self.tax_ids = False

    @api.depends('qty', 'unit_price', 'tax_ids')
    def _compute_total(self):
        for rec in self:
            tax_results = self.env['account.tax']._compute_taxes([rec._convert_to_tax_base_line_dict()])
            totals = next(iter(tax_results['totals'].values()))
            print("tax_results['totals']", tax_results['totals'])
            print("totals", totals)
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
            partner=self.office_purchase_id.vendor_id,
            currency=self.office_purchase_id.currency_id,
            product=self.product_id,
            taxes=self.tax_ids,
            price_unit=self.unit_price,
            quantity=self.qty,
            discount=0, #self.discount,
            price_subtotal=self.qty * self.unit_price,
        )

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    lpo_attach_rel = fields.Many2many('office.purchase', 'opo_attach_id', 'attach_id_office', 'doc_id_office',
                                      string="OPO Attachment", invisible=1)