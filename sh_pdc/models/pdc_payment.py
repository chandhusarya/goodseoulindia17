# Copyright (C) Softhealer Technologies.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.http import request
from datetime import datetime, date, timedelta


class Attachment(models.Model):
    _inherit = 'ir.attachment'

    pdc_id = fields.Many2one('pdc.wizard')


class PDC_wizard(models.Model):
    _name = "pdc.wizard"
    _description = "PDC Wizard"



    name = fields.Char("Name", default='New', readonly=True)
    payment_type = fields.Selection([('receive_money', 'Receive Money'), (
        'send_money', 'Send Money')], string="Payment Type", default='receive_money')
    partner_id = fields.Many2one('res.partner', string="Customer/Vendor")
    payment_amount = fields.Monetary("Payment Amount")
    currency_id = fields.Many2one(
        'res.currency', string="Currency", default=lambda self: self.env.company.currency_id)
    reference = fields.Char("Cheque Number", required=True)
    journal_id = fields.Many2one('account.journal', string="PDC Journal", required=True)
    deposit_journal_id = fields.Many2one('account.journal', string="Deposited Bank", domain=[
                                 ('type', '=', 'bank')])
    cheque_status = fields.Selection([('draft','Draft'),('deposit','Deposit'),('paid','Paid')],string="Cheque Status",default='draft')
    payment_date = fields.Date(
        "Cheque Received Date", default=fields.Date.today(), required=True)

    cheque_date = fields.Date("Cheque Date", required=True)
    cheque_clearing_date = fields.Date("Cheque Clearing/Bounced Date")


    memo = fields.Char("Memo")

    attachment_ids = fields.Many2many('ir.attachment', string='Cheque Image')
    company_id = fields.Many2one('res.company',string='company',default=lambda self: self.env.company)
    invoice_id = fields.Many2one('account.move', string="Invoice/Bill")
    state = fields.Selection([('draft', 'Draft'),
                              ('registered', 'Registered'),
                              ('cleared', 'Cleared'),
                              ('bounced', 'Bounced'),
                              ('cancel', 'Cancelled')], string="State", default='draft')

    move_register_id = fields.Many2one('account.move', string="Move Register")
    move_cleared_id = fields.Many2one('account.move', string="Move Cleared")
    move_bounced_id = fields.Many2one('account.move', string="Move Bounced")

    original_reconciled_moves = fields.Many2many('account.move.line', 'pdc_wizard_account_move', 'pdc_wizard_id',
                                    'move_id', string="Reconciled Move before Bouncing")

    is_reconciled = fields.Boolean("Is Reconciled", store=True, compute='_compute_reconciliation_status')
    is_matched = fields.Boolean("Is Matched", store=True, compute='_compute_reconciliation_status')

    bounced_pdc = fields.Many2one('pdc.wizard', string="Bounced PDC", tracking=True)


    def action_pdc_bounced(self):

        move_lines = []

        if not self.cheque_clearing_date:
            raise UserError(_('Please input cheque Clearing/bounced date'))

        # Entry to pdc journal
        mvl = {
            'name': 'PDC Bounced : ' + self.reference + ' : ' + self.name,
            'debit': self.payment_type == 'send_money' and self.payment_amount or 0,
            'credit': self.payment_type == 'receive_money' and self.payment_amount or 0,
            'partner_id': self.partner_id.id,
            'account_id': self.journal_id.default_account_id.id
        }
        move_lines.append((0, 0, mvl))

        # Entry to partner account
        mvl = {
            'name': 'PDC Bounced : ' + self.reference + ' : ' + self.name,
            'debit': self.payment_type == 'receive_money' and self.payment_amount or 0,
            'credit': self.payment_type == 'send_money' and self.payment_amount or 0,
            'partner_id': self.partner_id.id,
            'account_id': self.payment_type == 'receive_money' and self.partner_id.property_account_receivable_id.id or \
                          self.partner_id.property_account_payable_id.id
        }
        move_lines.append((0, 0, mvl))

        move = self.env['account.move'].create({
            'ref': self.name + " : Bounced",
            'name': '/',
            'journal_id': self.journal_id.id,
            'date': self.cheque_clearing_date,
            'line_ids': move_lines,
            'pdc_payment_id' : self.id
        })
        move.action_post()
        self.move_bounced_id = move.id
        self.state = "bounced"

        self.reconcile_for_pdc_bounced()


    def reconcile_for_pdc_bounced(self):

        r_liquidity_lines, r_counterpart_lines, r_writeoff_lines = self._seek_for_lines(self.move_register_id)

        b_liquidity_lines, b_counterpart_lines, b_writeoff_lines = self._seek_for_lines(self.move_bounced_id)

        reconciled_moves = []

        for counterpart_line in r_counterpart_lines:

            if counterpart_line.matched_debit_ids and counterpart_line.matched_debit_ids.debit_move_id:
                reconciled_moves.append(counterpart_line.matched_debit_ids.debit_move_id.id)

        if reconciled_moves:
            self.original_reconciled_moves = reconciled_moves
            self.env['account.move.line'].browse(reconciled_moves).remove_move_reconcile()

        #reconcile with pdc bounced entires
        r_counterpart_lines = r_counterpart_lines[0]
        b_counterpart_lines = b_counterpart_lines[0]
        to_reconcile = [r_counterpart_lines.id, b_counterpart_lines.id]
        self.env['account.move.line'].browse(to_reconcile).reconcile()



    def action_clear_pdc(self):

        if not self.deposit_journal_id:
            raise UserError(_('Please select Deposited Bank'))

        if not self.cheque_clearing_date:
            raise UserError(_('Please input cheque Clearing/Bounced date'))


        move_lines = []

        # Entry to bank account on which pdc is received
        account_id  = False
        if self.payment_type == 'send_money':

            outbound_payment_method_line = self.deposit_journal_id.outbound_payment_method_line_ids
            for outbound_line in outbound_payment_method_line:
                if outbound_line.payment_account_id:
                    account_id = outbound_line.payment_account_id.id

            if not account_id:
                account_id = self.deposit_journal_id.default_account_id.id

        else:

            inbound_payment_method_line_ids = self.deposit_journal_id.inbound_payment_method_line_ids
            for inbound_line in inbound_payment_method_line_ids:
                if inbound_line.payment_account_id:
                    account_id = inbound_line.payment_account_id.id

            if not account_id:
                account_id = self.deposit_journal_id.default_account_id.id


        mvl = {
            'name': 'PDC Cleared : ' + self.reference + ' : ' + self.name,
            'debit': self.payment_type == 'receive_money' and self.payment_amount or 0,
            'credit': self.payment_type == 'send_money' and self.payment_amount or 0,
            'partner_id': self.partner_id.id,
            'account_id': account_id
        }
        move_lines.append((0, 0, mvl))

        # Entry to pdc account

        mvl = {
            'name': 'PDC Cleared : ' + self.reference + ' : ' + self.name,
            'debit': self.payment_type == 'send_money' and self.payment_amount or 0,
            'credit': self.payment_type == 'receive_money' and self.payment_amount or 0,
            'partner_id': self.partner_id.id,
            'account_id': self.journal_id.default_account_id.id
        }
        move_lines.append((0, 0, mvl))

        move = self.env['account.move'].create({
            'ref': self.name  + " : Cleared",
            'name': '/',
            'journal_id': self.journal_id.id,
            'date': self.cheque_clearing_date,
            'line_ids': move_lines,
            'pdc_payment_id': self.id
        })
        move.action_post()
        self.move_cleared_id = move.id
        self.state = "cleared"





    def button_open_invoices(self):
        ''' Redirect the user to the invoice(s) paid by this payment.
        :return:    An action on account.move.
        '''
        self.ensure_one()

        action = {
            'name': _("Paid Invoices"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
        }
        if len(self.reconciled_invoice_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.reconciled_invoice_ids.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.reconciled_invoice_ids.ids)],
            })
        return action





    @api.depends('move_register_id.line_ids.amount_residual', 'move_register_id.line_ids.amount_residual_currency',
                 'move_register_id.line_ids.account_id')
    def _compute_reconciliation_status(self):
        ''' Compute the field indicating if the payments are already reconciled with something.
        This field is used for display purpose (e.g. display the 'reconcile' button redirecting to the reconciliation
        widget).
        '''
        for pay in self:
            liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines(self.move_register_id)

            if not pay.currency_id or not pay.id:
                pay.is_reconciled = False
                pay.is_matched = False
            elif pay.currency_id.is_zero(pay.payment_amount):
                pay.is_reconciled = True
                pay.is_matched = True
            else:
                residual_field = 'amount_residual' if pay.currency_id == pay.company_id.currency_id else 'amount_residual_currency'
                if pay.journal_id.default_account_id and pay.journal_id.default_account_id in liquidity_lines.account_id:
                    # Allow user managing payments without any statement lines by using the bank account directly.
                    # In that case, the user manages transactions only using the register payment wizard.
                    pay.is_matched = True
                else:
                    pay.is_matched = pay.currency_id.is_zero(sum(liquidity_lines.mapped(residual_field)))

                reconcile_lines = (counterpart_lines + writeoff_lines).filtered(lambda line: line.account_id.reconcile)
                pay.is_reconciled = pay.currency_id.is_zero(sum(reconcile_lines.mapped(residual_field)))


    def _seek_for_lines(self, move):
        ''' Helper used to dispatch the journal items between:
        - The lines using the temporary liquidity account.
        - The lines using the counterpart account.
        - The lines being the write-off lines.
        :return: (liquidity_lines, counterpart_lines, writeoff_lines)
        '''

        liquidity_lines = self.env['account.move.line']
        counterpart_lines = self.env['account.move.line']
        writeoff_lines = self.env['account.move.line']

        for line in move.line_ids:
            if line.account_id in self._get_valid_liquidity_accounts():
                liquidity_lines += line
            elif line.account_id.account_type in ('asset_receivable', 'liability_payable'):
                counterpart_lines += line
            else:
                writeoff_lines += line

        return liquidity_lines, counterpart_lines, writeoff_lines


    def _get_valid_liquidity_accounts(self):
        return (
            self.journal_id.default_account_id
        )


    def action_open_manual_reconciliation_widget(self):

        if self.bounced_pdc and self.bounced_pdc.original_reconciled_moves:
            return self.action_open_manual_reconciliation_widget_with_previous_pdc()
        else:
            return self.action_open_manual_reconciliation_widget_no_previous_pdc()



    def action_open_manual_reconciliation_widget_with_previous_pdc(self):
        ''' Open the manual reconciliation widget for the current payment.
        :return: A dictionary representing an action.
        '''
        self.ensure_one()

        if not self.partner_id:
            raise UserError(_("Payments without a customer can't be matched"))

        journal_items_to_reconcile = []
        for line in self.move_register_id.line_ids:
            if line.account_id.account_type in ('asset_receivable', 'liability_payable'):
                journal_items_to_reconcile.append(line.id)


        for original_reconciled in self.bounced_pdc.original_reconciled_moves:
            journal_items_to_reconcile.append(original_reconciled.id)



        return {
            'type': 'ir.actions.client',
            'name': _('Reconcile'),
            'tag': 'manual_reconciliation_view',
            'binding_model_id': self.env['ir.model.data']._xmlid_to_res_id('account.model_account_move_line'),
            'binding_type': 'action',
            'binding_view_types': 'list',
            'context': {'active_ids': journal_items_to_reconcile, 'active_model': 'account.move.line'},
        }




    def action_open_manual_reconciliation_widget_no_previous_pdc(self):
        ''' Open the manual reconciliation widget for the current payment.
        :return: A dictionary representing an action.
        '''
        self.ensure_one()

        if not self.partner_id:
            raise UserError(_("Payments without a customer can't be matched"))

        move_line_id = False
        for line in self.move_register_id.line_ids:
            if line.account_id.account_type in ('asset_receivable', 'liability_payable'):
                move_line_id = line.id

        action_context = {'company_ids': self.company_id.ids, 'partner_ids': self.partner_id.ids}
        if self.payment_type == 'receive_money':
            action_context.update({'mode': 'customers'})
        elif self.payment_type == 'send_money':
            action_context.update({'mode': 'suppliers'})

        if move_line_id:
            action_context.update({'move_line_id': move_line_id})

        return {
            'type': 'ir.actions.client',
            'tag': 'manual_reconciliation_view',
            'context': action_context,
        }





    def action_register(self):

        move_lines = []

        #Entry to pdc journal
        mvl = {
            'name' : 'PDC Registered : ' + self.reference + ' : ' + self.name,
            'debit' : self.payment_type == 'receive_money' and self.payment_amount or 0,
            'credit' : self.payment_type == 'send_money' and self.payment_amount or 0,
            'partner_id' : self.partner_id.id,
            'account_id' : self.journal_id.default_account_id.id
        }
        move_lines.append((0, 0, mvl))

        #Entry to partner account
        mvl = {
            'name': 'PDC Registered : ' + self.reference + ' : ' + self.name,
            'debit' : self.payment_type == 'send_money' and self.payment_amount or 0,
            'credit' : self.payment_type == 'receive_money' and self.payment_amount or 0,
            'partner_id': self.partner_id.id,
            'account_id': self.payment_type == 'receive_money' and self.partner_id.property_account_receivable_id.id or \
                          self.partner_id.property_account_payable_id.id
        }
        move_lines.append((0, 0, mvl))


        move = self.env['account.move'].create({
            'ref': self.name  + " : Registered",
            'name': '/',
            'journal_id': self.journal_id.id,
            'date': self.payment_date,
            'line_ids': move_lines,
            'pdc_payment_id': self.id
        })
        move.action_post()
        self.move_register_id = move.id
        self.state = "registered"




    def action_cancel(self):
        self.write({'state': 'cancel'})

    @api.model
    def create(self, vals):

        print("\n\n\nvals ====>> ", vals)
        if vals.get('payment_type') == 'receive_money':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'pdc.payment.customer')
        elif vals.get('payment_type') == 'send_money':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'pdc.payment.vendor')

        res = super(PDC_wizard, self).create(vals)
        # fix attachment ownership
        for template in res:
            if template.attachment_ids:
                template.attachment_ids.sudo().write({'res_model': self._name, 'res_id': template.id})
        return res


    def pdc_notification(self):

        print("ddddddddddddddddddd")

        now = datetime.now()
        date_now = now.date()
        reminder_days = 5

        cheque_date = date_now + timedelta(days=reminder_days)

        upcoming_pdc = self.search([('cheque_date', '<=', cheque_date), ('state', '=', 'registered')])

        if upcoming_pdc:

            mail_content = "  Hello,<br>Please find below list of PDC going to clear within<br>"

            for pdc in upcoming_pdc:

                payment_type = pdc.payment_type == 'receive_money' and 'Receive Money' or 'Send Money'

                mail_content = mail_content + "<br><b>Customer/Vendor : </b>" + pdc.partner_id.name + ", <b>Type: </b>" + payment_type + \
                               ", <b>PDC Number: </b>" + pdc.name + ", <b>Cheque Date: </b>" + str(pdc.cheque_date) + ", <b>Amount: </b>" + str(pdc.payment_amount)

            users = self.env.ref('sh_pdc.group_get_pdc_notification').users
            email_to = ""
            for usr in users:
                if usr.partner_id.email:
                    if not email_to:
                        email_to = usr.partner_id.email
                    else:
                        email_to = email_to + ', ' + usr.partner_id.email

            main_content = {
                'subject': _('PDC Notification'),
                'author_id': self.env.user.partner_id.id,
                'body_html': mail_content,
                'email_to': email_to,
            }
            self.env['mail.mail'].create(main_content).send()







    
