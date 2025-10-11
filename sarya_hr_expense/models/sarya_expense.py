# models/expense_advance.py
from odoo import models, fields, api, _
from odoo.tools import email_split, float_repr, float_round, is_html_empty
from odoo.exceptions import ValidationError, UserError

class ExpenseAdvanceRequest(models.Model):
    _name = 'expense.advance.request'
    _description = 'Employee Advance Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # @api.model
    # def _default_journal_id(self):
    #     """
    #          The journal is determining the company of the accounting entries generated from expense.
    #          We need to force journal company and expense sheet company to be the same.
    #     """
    #     company_journal_id = self.env.company.expense_journal_id
    #     if company_journal_id:
    #         return company_journal_id.id
    #     default_company_id = self.default_get(['company_id'])['company_id']
    #     journal = self.env['account.journal'].search([
    #         *self.env['account.journal']._check_company_domain(default_company_id),
    #         ('type', '=', 'purchase'),
    #     ], limit=1)
    #     return journal.id

    name = fields.Char("Description")
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, default=lambda self: self.env.user.employee_id , tracking=True)
    manager_id = fields.Many2one('hr.employee', string='Manager', related='employee_id.parent_id', store=True)
    company_id = fields.Many2one(comodel_name='res.company',
                                 string='Company',
                                 default=lambda self: self.env.company,
                                 readonly=True)

    employee_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Journal",
        check_company=True,
        domain=[('type', '=', 'purchase')],
        help="The journal used when the expense is paid by employee.", tracking=True
    )

    payment_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Payment Journal", tracking=True
    )
    deposit_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Deposit Journal", tracking=True
    )


    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('manager_approved', 'Manager Approved'),
        ('hr_approved', 'HR Approved'),

        ('advance_finance_approved', 'Advance Finance Approved'),
        ('direct_finance_approved', 'Direct Finance Approved'),

        ('advance_waiting_for_actual', 'Waiting for actual expense'),
        ('advance_actual_expense_submitted', 'Actual expense submitted'),

        ('completed', 'Completed')
    ], default='draft', tracking=True)

    exp_type = fields.Selection([('direct', 'Direct'),
                                 ('advance', 'Advance')],
                                string='Expense Type', tracking=True, default='advance')

    line_ids = fields.One2many('expense.advance.request.line', 'request_id', string='Advance Lines')
    total_requested = fields.Float(compute='_compute_totals', string='Total Requested')
    total_actual = fields.Float(compute='_compute_totals', string='Total Actual')
    difference = fields.Float(compute='_compute_totals', string='Difference')

    tax_amount = fields.Float(compute='_compute_totals', string='Tax Amount')
    untaxed_amount = fields.Float(compute='_compute_totals', string='UnTaxed Amount')



    direct_entry_posted = fields.Many2one('account.move', string='Direct entry posted')

    advance_entry_posted = fields.Many2one('account.move', string='Advance entry posted')

    advance_settlement = fields.Many2one('account.move', string='Advance settlement')

    advance_payment_issued = fields.Many2one('account.move', string='Advance payment issued')

    advance_payment_settlement = fields.Many2one('account.move', string='Advance Settlement payment')

    direct_payment_issued = fields.Many2one('account.move', string='Direct expense payment issued')

    advance_account = fields.Many2one('account.account', string='Advance account')
    employee_payable = fields.Many2one('account.account', string='Employee Payable account')

    advance_amount = fields.Float(compute='_compute_advance_amount', string='Advance Balance')

    can_do_manager_approval = fields.Boolean(compute='_check_can_do_manager_approval', string="Can do manager approval")

    can_do_hr_approval = fields.Boolean(compute='_check_can_do_hr_approval', string="Can do Hr approval")

    pending_to_pay_advance = fields.Boolean(compute='_check_pending_to_pay_advance', string="Advance not paid")

    pending_to_pay_advance_settlement = fields.Boolean(compute='_check_pending_to_pay_advance_settlement',
                                                       string="Advance settlement not paid")

    pending_to_pay_direct = fields.Boolean(compute='_check_pending_to_pay_direct',
                                                       string="Expense not paid")

    submitted_date = fields.Datetime("Submitted Date")
    manager_approved_date = fields.Datetime("Manager Approved")
    hr_approved_date = fields.Datetime("HR Approved Date")
    finance_posted_date = fields.Datetime("Finance Posted Date")
    asked_for_actual_date = fields.Datetime("Asked for actual expense Date")
    actual_submitted_date = fields.Datetime("Actual Submitted Date")
    completed_date = fields.Datetime("Completed Date")
    advance_payment_issued_date = fields.Datetime("Advance Payment Issued Date")
    advance_payment_settled_date = fields.Datetime("Advance Payment Settled Date")

    direct_payment_issued_date = fields.Datetime("Direct expense Payment Issued Date")



    def register_direct_payment(self):

        if not self.payment_journal_id:
            raise UserError(_("Please Select payment journal"))

        line_ids = []
        total_expense = self.total_actual
        advance_deduct_amount = 0.0
        direct_amount_credit = 0.0
        if self.advance_amount > 0:
            if self.advance_amount > total_expense:
                advance_deduct_amount = total_expense
                direct_amount_credit = 0.0
            else:
                advance_deduct_amount = total_expense - self.advance_amount
                # advance_deduct_amount = total_expense
                direct_amount_credit = advance_deduct_amount

        #Debit payable account
        if total_expense > 0.0:
            line_ids.append((0, 0, {
                'account_id': self.employee_payable.id,
                'name': self.name + " - Direct Expense Payment issued",
                'partner_id': self.employee_id.work_contact_id.id,
                'debit': total_expense,
                'credit': 0.0,
            }))

        account_id = False
        outbound_payment_method_line = self.payment_journal_id.outbound_payment_method_line_ids
        for outbound_line in outbound_payment_method_line:
            if outbound_line.payment_account_id:
                account_id = outbound_line.payment_account_id.id

        if not account_id:
            account_id = self.deposit_journal_id.default_account_id.id

        if direct_amount_credit > 0.0:
            line_ids.append((0, 0, {
                'account_id': account_id,
                'name': self.name + " Direct Expense Payment issued",
                'partner_id': self.employee_id.work_contact_id.id,
                'debit': 0.0,
                'credit': direct_amount_credit,
            }))
        if self.advance_amount > 0:
            line_ids.append((0, 0, {
                'account_id': self.advance_account.id,
                'name': self.name + " Extra Amount Deduction from advance",
                'partner_id': self.employee_id.work_contact_id.id,
                'debit': 0.0,
                'credit': advance_deduct_amount,
            }))

        # journal_id = self.env['ir.config_parameter'].sudo().get_param('hr_expense.journal_id')

        move_vals = {
            'ref': 'Advance Payment issued : ' + self.name,
            'journal_id': self.payment_journal_id.id,
            'partner_id': self.employee_id.work_contact_id.id,
            'date': fields.Date.today(),
            "line_ids": line_ids
        }

        # Create and post the journal entry
        move = self.env['account.move'].create(move_vals)
        move.action_post()

        self.direct_payment_issued = move.id
        self.direct_payment_issued_date = fields.Datetime.now()

        #Reconcile payable from advance payed and employee pyament
        to_reconcile = []

        employee_payable = self.employee_payable.id

        if self.direct_entry_posted and self.direct_entry_posted.state == 'posted':
            for line in self.direct_entry_posted.line_ids:
                if line.account_id.id == employee_payable:
                    if line.amount_residual != 0:
                        to_reconcile.append(line.id)


        if self.direct_payment_issued and self.direct_payment_issued.state == 'posted':
            for line in self.direct_payment_issued.line_ids:
                if line.account_id.id == employee_payable:
                    if line.amount_residual != 0:
                        to_reconcile.append(line.id)


        if len(to_reconcile) > 1:
            self.env['account.move.line'].browse(to_reconcile).reconcile()
        else:
            self.message_post(
                body='Cannot do auto reconcile for direct payment',
                subject='Auto reconcile failed',
                message_type='comment',  # 'comment', 'notification', or 'email'
                subtype_xmlid='mail.mt_note',  # 'mail.mt_note' for internal note
            )





    def register_advance_settlement_payment(self):

        if not self.payment_journal_id:
            raise UserError(_("Please Select payment journal"))

        amount_to_pay = 0

        if self.advance_settlement and self.advance_settlement.state == 'posted':
            for line in self.advance_settlement.line_ids:
                if line.account_id.id == self.employee_payable.id and line.amount_residual != 0:
                    amount_to_pay = abs(line.amount_residual)

        if amount_to_pay < 0.001:
            raise UserError(_("Amount to pay is %s. Please check" % str(amount_to_pay)))

        line_ids = []

        #Debit payable account
        line_ids.append((0, 0, {
            'account_id': self.employee_payable.id,
            'name': self.name + " - Advance Settlement Payment",
            'partner_id': self.employee_id.work_contact_id.id,
            'debit': amount_to_pay,
            'credit': 0.0,
        }))

        account_id = False
        outbound_payment_method_line = self.payment_journal_id.outbound_payment_method_line_ids
        for outbound_line in outbound_payment_method_line:
            if outbound_line.payment_account_id:
                account_id = outbound_line.payment_account_id.id

        if not account_id:
            account_id = self.deposit_journal_id.default_account_id.id


        line_ids.append((0, 0, {
            'account_id': account_id,
            'name': self.name + " Advance Settlement Payment",
            'partner_id': self.employee_id.work_contact_id.id,
            'debit': 0.0,
            'credit': amount_to_pay,
        }))

        # journal_id = self.env['ir.config_parameter'].sudo().get_param('hr_expense.journal_id')

        move_vals = {
            'ref': 'Advance Settlement Payment : ' + self.name,
            'journal_id': self.payment_journal_id.id,
            'partner_id': self.employee_id.work_contact_id.id,
            'date': fields.Date.today(),
            "line_ids": line_ids
        }

        # Create and post the journal entry
        move = self.env['account.move'].create(move_vals)
        move.action_post()

        self.advance_payment_settlement = move.id
        self.advance_payment_settled_date = fields.Datetime.now()

        #Reconcile payable from advance payed and employee pyament
        to_reconcile = []

        employee_payable = self.employee_payable.id

        if self.advance_settlement and self.advance_settlement.state == 'posted':
            for line in self.advance_settlement.line_ids:
                if line.account_id.id == employee_payable:
                    if line.amount_residual != 0:
                        to_reconcile.append(line.id)


        if self.advance_payment_settlement and self.advance_payment_settlement.state == 'posted':
            for line in self.advance_payment_settlement.line_ids:
                if line.account_id.id == employee_payable:
                    if line.amount_residual != 0:
                        to_reconcile.append(line.id)


        if len(to_reconcile) > 1:
            self.env['account.move.line'].browse(to_reconcile).reconcile()
        else:
            self.message_post(
                body='Cannot do auto reconcile for advance settlement payment',
                subject='Auto reconcile failed',
                message_type='comment',  # 'comment', 'notification', or 'email'
                subtype_xmlid='mail.mt_note',  # 'mail.mt_note' for internal note
            )







    def register_advance_payment(self):

        if not self.payment_journal_id:
            raise UserError(_("Please Select payment journal"))

        line_ids = []

        #Debit payable account
        line_ids.append((0, 0, {
            'account_id': self.employee_payable.id,
            'name': self.name + " - Advance Payment issued",
            'partner_id': self.employee_id.work_contact_id.id,
            'debit': self.total_requested,
            'credit': 0.0,
        }))

        account_id = False
        outbound_payment_method_line = self.payment_journal_id.outbound_payment_method_line_ids
        for outbound_line in outbound_payment_method_line:
            if outbound_line.payment_account_id:
                account_id = outbound_line.payment_account_id.id

        if not account_id:
            account_id = self.deposit_journal_id.default_account_id.id


        line_ids.append((0, 0, {
            'account_id': account_id,
            'name': self.name + " Advance Payment issued",
            'partner_id': self.employee_id.work_contact_id.id,
            'debit': 0.0,
            'credit': self.total_requested,
        }))

        # journal_id = self.env['ir.config_parameter'].sudo().get_param('hr_expense.journal_id')

        move_vals = {
            'ref': 'Advance Payment issued : ' + self.name,
            'journal_id': self.payment_journal_id.id,
            'partner_id': self.employee_id.work_contact_id.id,
            'date': fields.Date.today(),
            "line_ids": line_ids
        }

        # Create and post the journal entry
        move = self.env['account.move'].create(move_vals)
        move.action_post()

        self.advance_payment_issued = move.id
        self.advance_payment_issued_date = fields.Datetime.now()

        #Reconcile payable from advance payed and employee pyament
        to_reconcile = []

        employee_payable = self.employee_payable.id

        if self.advance_entry_posted and self.advance_entry_posted.state == 'posted':
            for line in self.advance_entry_posted.line_ids:
                if line.account_id.id == employee_payable:
                    if line.amount_residual != 0:
                        to_reconcile.append(line.id)


        if self.advance_payment_issued and self.advance_payment_issued.state == 'posted':
            for line in self.advance_payment_issued.line_ids:
                if line.account_id.id == employee_payable:
                    if line.amount_residual != 0:
                        to_reconcile.append(line.id)


        if len(to_reconcile) > 1:
            self.env['account.move.line'].browse(to_reconcile).reconcile()
        else:
            self.message_post(
                body='Cannot do auto reconcile for advance payment',
                subject='Auto reconcile failed',
                message_type='comment',  # 'comment', 'notification', or 'email'
                subtype_xmlid='mail.mt_note',  # 'mail.mt_note' for internal note
            )





    def _check_pending_to_pay_direct(self):
        for request in self:
            pending_to_pay_direct = False
            if request.direct_entry_posted and request.direct_entry_posted.state == 'posted':
                employee_payable = request.employee_payable.id
                for line in request.direct_entry_posted.line_ids:
                    if line.account_id.id == employee_payable:
                        if line.amount_residual != 0:
                            pending_to_pay_direct = True
            request.pending_to_pay_direct = pending_to_pay_direct



    def _check_pending_to_pay_advance_settlement(self):
        for request in self:
            pending_to_pay_advance_settlement = False
            if request.advance_settlement and request.advance_settlement.state == 'posted':
                employee_payable = request.employee_payable.id
                for line in request.advance_settlement.line_ids:
                    if line.account_id.id == employee_payable:
                        if line.amount_residual != 0:
                            pending_to_pay_advance_settlement = True
            request.pending_to_pay_advance_settlement = pending_to_pay_advance_settlement

    def _check_pending_to_pay_advance(self):
        for request in self:
            pending_to_pay_advance = False
            if request.advance_entry_posted and request.advance_entry_posted.state == 'posted':
                employee_payable = request.employee_payable.id

                for line in request.advance_entry_posted.line_ids:
                    if line.account_id.id == employee_payable:
                        if line.amount_residual != 0:
                            pending_to_pay_advance = True

            request.pending_to_pay_advance = pending_to_pay_advance



    def _check_can_do_hr_approval(self):
        for request in self:
            can_do_hr_approval = True
            if not self.env.user.has_group('sarya_hr_expense.can_do_expense_hr_approval'):
                can_do_hr_approval = False
            else:
                if request.state == 'submitted':
                    if request.manager_id:
                        can_do_hr_approval = False

                elif request.state != 'manager_approved':
                    can_do_hr_approval = False

            request.can_do_hr_approval = can_do_hr_approval




    def submit_expense(self):
        for request in self:
            request.state = 'submitted'
            request.submitted_date = fields.Datetime.now()

            if request.can_do_manager_approval:
                mail_content = "Hello,<br>Please check and approve expense %s submitted by %s" % (
                request.name, request.employee_id.name)


                email_to = request.manager_id.work_email

                main_content = {
                    'subject': _('India: Employee Expense Approval'),
                    'author_id': self.env.user.partner_id.id,
                    'body_html': mail_content,
                    'email_to': email_to,
                }
                self.env['mail.mail'].sudo().create(main_content).send()


            elif request.can_do_hr_approval:
                mail_content = "Hello,<br>Please check and approve expense %s submitted by %s" % (request.name, request.employee_id.name)

                users = self.env.ref('sarya_hr_expense.can_do_expense_hr_approval').users
                email_to = ""
                for usr in users:
                    if usr.partner_id.email:
                        if not email_to:
                            email_to = usr.partner_id.email
                        else:
                            email_to = email_to + ', ' + usr.partner_id.email

                main_content = {
                    'subject': _('India: Employee Expense Approval'),
                    'author_id': self.env.user.partner_id.id,
                    'body_html': mail_content,
                    'email_to': email_to,
                }
                self.env['mail.mail'].sudo().create(main_content).send()



    def _check_can_do_manager_approval(self):
        for request in self:
            can_do_manager_approval = True
            if request.state != 'submitted':
                can_do_manager_approval = False
            else:
                if not request.manager_id:
                    can_do_manager_approval = False
                elif not request.manager_id.user_id:
                    can_do_manager_approval = False
                elif self.env.uid != request.manager_id.user_id.id:
                    can_do_manager_approval = False
            request.can_do_manager_approval = can_do_manager_approval



    @api.depends('request_id.exp_type', 'request_id.state')
    def _can_input_amount(self):
        for rec in self:
            can_input_advance_amount = False
            can_input_actual_amount = False

            request_id = rec.request_id
            if request_id.exp_type == 'direct':
                if request_id.state == 'draft':
                    can_input_actual_amount = True
            else:
                if request_id.state == 'draft':
                    can_input_advance_amount = True

                if request_id.state == 'advance_waiting_for_actual':
                    can_input_actual_amount = True

            rec.can_input_advance_amount = can_input_advance_amount
            rec.can_input_actual_amount = can_input_actual_amount

    def submit_actual_expense(self):
        self.state = 'advance_actual_expense_submitted'
        self.actual_submitted_date = fields.Datetime.now()

        mail_content = "Hello,<br>Actual expense of %s is submitted" % (self.name)
        email_to = self.employee_id.work_email
        main_content = {
            'subject': _('India: Actual Expense Submitted'),
            'author_id': self.env.user.partner_id.id,
            'body_html': mail_content,
            'email_to': email_to,
        }
        self.env['mail.mail'].sudo().create(main_content).send()



    @api.depends('state', 'employee_id')
    def _compute_advance_amount(self):
        for rec in self:
            advance_amount = 0
            if rec.employee_id:
                partner_id = self.employee_id.work_contact_id
                if partner_id and rec.advance_account:
                    advance_account = rec.advance_account.id
                    lines = self.env['account.move.line'].search([
                        ('partner_id', '=', partner_id.id),
                        ('account_id', '=', advance_account),
                        ('move_id.state', '=', 'posted'),
                    ])

                    debit = sum(lines.mapped('debit'))
                    credit = sum(lines.mapped('credit'))
                    advance_amount = debit - credit

            rec.advance_amount = advance_amount



    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for exp in self:
            exp.employee_payable = exp.employee_id.work_contact_id.property_account_payable_id.id

    @api.onchange('exp_type')
    def _onchange_exp_type(self):
        for exp in self:
            if exp.exp_type == 'advance':
                account_id = self.env['ir.config_parameter'].sudo().get_param('hr_expense.advance_account_id')
                if account_id:
                    exp.advance_account = int(account_id)


    @api.depends('line_ids')
    def _compute_totals(self):
        for rec in self:
            rec.total_requested = sum(line.advance_amount for line in rec.line_ids)
            rec.total_actual = sum(line.actual_amount for line in rec.line_ids)

            rec.tax_amount = sum(line.tax_amount for line in rec.line_ids)
            rec.untaxed_amount = sum(line.untaxed_amount for line in rec.line_ids)

            rec.difference = rec.total_requested - rec.total_actual

    def action_manager_approve(self):
        for request in self:
            request.write({'state': 'manager_approved'})
            request.manager_approved_date = fields.Datetime.now()

            mail_content = "Hello,<br>Please check and approve expense %s submitted by %s" % (
            request.name, request.employee_id.name)

            users = self.env.ref('sarya_hr_expense.can_do_expense_hr_approval').users
            email_to = ""
            for usr in users:
                if usr.partner_id.email:
                    if not email_to:
                        email_to = usr.partner_id.email
                    else:
                        email_to = email_to + ', ' + usr.partner_id.email

            main_content = {
                'subject': _('India: Employee Expense Approval'),
                'author_id': self.env.user.partner_id.id,
                'body_html': mail_content,
                'email_to': email_to,
            }
            self.env['mail.mail'].sudo().create(main_content).send()



    def action_hr_approve(self):

        for request in self:
            request.write({'state': 'hr_approved'})
            request.hr_approved_date = fields.Datetime.now()

            mail_content = "Hello,<br>Please check and post expense %s submitted by %s" % (
                request.name, request.employee_id.name)

            users = self.env.ref('sarya_hr_expense.can_do_expense_finance_approval').users
            email_to = ""
            for usr in users:
                if usr.partner_id.email:
                    if not email_to:
                        email_to = usr.partner_id.email
                    else:
                        email_to = email_to + ', ' + usr.partner_id.email

            main_content = {
                'subject': _('India: Employee Expense Posting'),
                'author_id': self.env.user.partner_id.id,
                'body_html': mail_content,
                'email_to': email_to,
            }
            self.env['mail.mail'].sudo().create(main_content).send()




    def action_disburse(self):
        self.write({'state': 'disbursed'})


    def ask_to_submit_actual(self):
        if self.pending_to_pay_advance:
            raise UserError(_("Please issue payment to employee"))
        self.state = 'advance_waiting_for_actual'
        self.asked_for_actual_date = fields.Datetime.now()

        mail_content = "Hello,<br>Please submit actual bills and amount for expense %s " % (self.name)

        email_to = self.employee_id.work_email

        main_content = {
            'subject': _('India: Requested Actual Bills'),
            'author_id': self.env.user.partner_id.id,
            'body_html': mail_content,
            'email_to': email_to,
        }
        self.env['mail.mail'].sudo().create(main_content).send()


    def finance_approve_advance(self):
        print("\n\n\n================= finance_approve_advance =================\n\n\n")

        self.state = 'advance_finance_approved'

        line_ids = []

        total_advance_amount = 0
        for line in self.line_ids:
            line_ids.append((0, 0, {
                'account_id': self.advance_account.id,
                'name': self.name + " - " + line.product_id.name  if line.product_id.name else "" + " - " + line.description if line.description else "",
                'partner_id': self.employee_id.work_contact_id.id,
                'debit': line.advance_amount,
                'credit': 0.0,
            }))
            total_advance_amount += line.advance_amount

            # Create Liability
        line_ids.append((0, 0, {
            'account_id': self.employee_payable.id,
            'name': self.name + " Expense Advance",
            'partner_id': self.employee_id.work_contact_id.id,
            'debit': 0.0,
            'credit': total_advance_amount,
        }))

        # journal_id = self.env['ir.config_parameter'].sudo().get_param('hr_expense.journal_id')

        move_vals = {
            'ref': 'Expense Advance : ' + self.name,
            'journal_id': self.employee_journal_id.id,
            'partner_id': self.employee_id.work_contact_id.id,
            'date': fields.Date.today(),
            "line_ids": line_ids
        }

        # Create and post the journal entry
        move = self.env['account.move'].create(move_vals)
        move.action_post()

        self.advance_entry_posted = move.id
        self.finance_posted_date = fields.Datetime.now()

        #Notification

        mail_content = "Hello,<br>Your expense expense %s approved" % (self.name)

        email_to = self.employee_id.work_email

        main_content = {
            'subject': _('India: Expense Approved'),
            'author_id': self.env.user.partner_id.id,
            'body_html': mail_content,
            'email_to': email_to,
        }
        self.env['mail.mail'].sudo().create(main_content).send()



    def post_actual_against_advance(self):

        self.state = 'completed'

        line_ids = []
        extra_to_pay = 0
        extra_advance_amount = self.advance_amount
        advance_amt_sum = 0
        for line in self.line_ids:

            actual_expense = line.actual_amount
            advance_to_credit = line.actual_amount

            line_ids.append((0, 0, {
                'account_id': line.account_id.id,
                'name': self.name + " - " + line.product_id.name + " - " + line.description,
                'partner_id': self.employee_id.work_contact_id.id,
                'tax_ids': line.tax_ids,
                'debit': line.untaxed_amount,
                'credit': 0.0,
                'analytic_distribution': line.analytic_distribution
            }))



            if line.actual_amount > line.advance_amount:
                advance_to_credit = line.advance_amount
                extra_to_pay = extra_to_pay + (line.actual_amount - line.advance_amount)
            advance_amt_sum = advance_amt_sum + line.advance_amount

            # if self.advance_amount:
            # if line.actual_amount < line.advance_amount:

            line_ids.append((0, 0, {
                'account_id': self.advance_account.id,
                'name': self.name + " - " + line.product_id.name + " - " + line.description,
                'partner_id': self.employee_id.work_contact_id.id,
                'debit': 0.00,
                'credit': advance_to_credit,
            }))

        if extra_advance_amount > 0:
            extra_advance_amount = extra_advance_amount - advance_amt_sum


        if extra_to_pay > 0:

            #if there is any extra amount to pay, check is there any exta advance amount
            if extra_advance_amount > 0:

                # advance_amount_to_deduct = extra_to_pay
                if extra_advance_amount < extra_to_pay:
                    advance_amount_to_deduct = extra_advance_amount
                else:
                    advance_amount_to_deduct = extra_to_pay
                    extra_to_pay = 0

                extra_to_pay = extra_to_pay - advance_amount_to_deduct

                line_ids.append((0, 0, {
                    'account_id': self.advance_account.id,
                    'name': self.name + " Extra Amount Deduction from advance",
                    'partner_id': self.employee_id.work_contact_id.id,
                    'debit': 0.00,
                    'credit': advance_amount_to_deduct,
                }))

            if extra_to_pay > 0:
                # if self.advance_amount:
                #     extra_to_pay = self.advance_amount

                line_ids.append((0, 0, {
                    'account_id': self.employee_payable.id,
                    'name': self.name + " Extra Amount",
                    'partner_id': self.employee_id.work_contact_id.id,
                    'debit': 0.0,
                    'credit': extra_to_pay,
                }))

        move_vals = {
            'ref': 'Expense Settlement : ' + self.name,
            'journal_id': self.employee_journal_id.id,
            'partner_id': self.employee_id.work_contact_id.id,
            'date': fields.Date.today(),
            "line_ids": line_ids
        }

        # Create and post the journal entry
        move = self.env['account.move'].create(move_vals)
        move.action_post()

        self.advance_settlement = move.id
        self.completed_date = fields.Datetime.now()



    def finance_approve_direct(self):
        self.state = 'completed'
        line_ids = []
        total_expense = 0
        for line in self.line_ids:

            actual_expense = line.actual_amount
            total_expense += actual_expense
            line_ids.append((0, 0, {
                'account_id': line.account_id.id,
                'name': self.name + " - " + line.product_id.name + " - " + line.description if line.description else "",
                'partner_id': self.employee_id.work_contact_id.id,
                'tax_ids': line.tax_ids,
                'debit': line.untaxed_amount,
                'credit': 0.0,
                'analytic_distribution': line.analytic_distribution
            }))


        line_ids.append((0, 0, {
            'account_id': self.employee_payable.id,
            'name': self.name + " Extra Amount",
            'partner_id': self.employee_id.work_contact_id.id,
            'debit': 0.0,
            'credit': total_expense,
        }))

        move_vals = {
            'ref': 'Expense Direct : ' + self.name,
            'journal_id': self.employee_journal_id.id,
            'partner_id': self.employee_id.work_contact_id.id,
            'date': fields.Date.today(),
            "line_ids": line_ids
        }

        # Create and post the journal entry
        move = self.env['account.move'].create(move_vals)
        move.action_post()

        self.direct_entry_posted = move.id
        self.finance_posted_date = fields.Datetime.now()
        self.completed_date = fields.Datetime.now()


    def action_reconcile(self):
        self.write({'state': 'reconciled'})

class ExpenseAdvanceRequestLine(models.Model):
    _name = 'expense.advance.request.line'
    _description = 'Advance Request Line'
    _inherit = ['analytic.mixin']


    request_id = fields.Many2one('expense.advance.request', string='Request')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company,
                                 readonly=True)
    currency_id = fields.Many2one( comodel_name='res.currency',  string='Currency', related='company_id.currency_id')
    state = fields.Selection(related="request_id.state")
    exp_type = fields.Selection([('direct', 'Direct'),
                                 ('advance', 'Advance')],
                                string='Expense Type', tracking=True, default='advance')
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Category",
        tracking=True,
        check_company=True,
        domain=[('can_be_expensed', '=', True)],
        ondelete='restrict',
    )
    description = fields.Char(string='Description')
    advance_amount = fields.Float(string='Advance Amount')
    actual_amount = fields.Float(string='Actual Amount')
    account_id = fields.Many2one('account.account', string='Expense Account')
    attachment_ids = fields.One2many(
        comodel_name='ir.attachment',
        inverse_name='res_id',
        domain="[('res_model', '=', 'expense.advance.request.line')]",
        string="Attachments",
    )

    can_input_advance_amount = fields.Boolean(compute='_can_input_amount', string="Can input advance amount")
    can_input_actual_amount = fields.Boolean(compute='_can_input_amount', string="Can input actual amount")

    tax_ids = fields.Many2many(
        comodel_name='account.tax',
        relation='sarya_expense_tax',
        column1='expense_id',
        column2='tax_id',
        string="Included taxes",
        store=True, readonly=False,
        domain="[('company_id', '=', company_id), ('type_tax_use', '=', 'purchase')]",
        help="Both price-included and price-excluded taxes will behave as price-included taxes for expenses.",
    )

    tax_amount = fields.Float(string="Tax amount", compute='_compute_tax_amount', precompute=True, store=True)
    untaxed_amount = fields.Float(string="Total Untaxed Amount In Currency", compute='_compute_tax_amount', precompute=True, store=True)

    def unlink(self):
        for line in self:
            if line.state != 'draft':
                raise UserError(_("You cannot delete line"))
        return super(ExpenseAdvanceRequestLine, self).unlink()



    @api.depends('actual_amount', 'tax_ids')
    def _compute_tax_amount(self):
        """
             Note: as total_amount_currency can be set directly by the user (for product without cost)
             or needs to be computed (for product with cost), `untaxed_amount_currency` can't be computed in the same method as `total_amount_currency`.
        """
        for expense in self:
            base_lines = [expense._convert_to_tax_base_line_dict(price_unit=expense.actual_amount)]
            taxes_totals = self.env['account.tax']._compute_taxes(base_lines)['totals'][expense.currency_id]
            expense.tax_amount = taxes_totals['amount_tax']
            expense.untaxed_amount = taxes_totals['amount_untaxed']

    def _convert_to_tax_base_line_dict(self, base_line=None, currency=None, price_unit=None, quantity=None):
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            base_line,
            currency=currency or self.currency_id,
            product=self.product_id,
            taxes=self.tax_ids,
            price_unit= self.actual_amount,
            quantity= 1,
            account= self.account_id,
            analytic_distribution=self.analytic_distribution,
            extra_context={'force_price_include': True},
        )



    def action_get_attachment_view(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window']._for_xml_id('base.action_attachment')
        res.update({
            'domain': [('res_model', '=', 'expense.advance.request.line'), ('res_id', 'in', self.ids)],
            'context': {'default_res_model': 'expense.advance.request.line', 'default_res_id': self.id},
        })
        return res




    @api.depends('request_id.exp_type', 'request_id.state')
    def _can_input_amount(self):
        for rec in self:
            can_input_advance_amount = False
            can_input_actual_amount = False

            request_id = rec.request_id
            if request_id.exp_type == 'direct':
                if request_id.state == 'draft':
                    can_input_actual_amount = True
            else:
                if request_id.state == 'draft':
                    can_input_advance_amount = True

                if request_id.state == 'advance_waiting_for_actual':
                    can_input_actual_amount = True

            rec.can_input_advance_amount = can_input_advance_amount
            rec.can_input_actual_amount = can_input_actual_amount


    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.description = line.product_id.description
                line.account_id = line.product_id.property_account_expense_id.id
            else:
                line.description = ""
                line.account_id = False




