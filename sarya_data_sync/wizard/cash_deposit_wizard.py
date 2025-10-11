# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.tools.misc import format_date, formatLang
from odoo.exceptions import ValidationError


class CashDepositWizard(models.TransientModel):
    _name = 'cash.deposit.wizard'
    _description = 'Cash Deposit wizard'

    manager_amount = fields.Float(
        string='Manager Amount',
        help='Transfer Amount To Manager Account'
    )
    manager_reason = fields.Char(
        string='Manager Reason'
    )
    petty_cash_amount = fields.Float(
        string='Petty Cash Amount',
        help='Transfer Amount To Petty Cash Account'
    )
    petty_cash_reason = fields.Char(
        string='Petty Cash Reason'
    )
    cash_statement_id = fields.Many2one(
        comodel_name='cash.statement',
        string='Cash Statement'
    )
    is_manager_deposit = fields.Boolean(
        string='Manager Deposit',
        help='identify the record is manager deposit.'
    )
    is_petty_cash_deposit = fields.Boolean(
        string='Manager Deposit',
        help='identify the record is petty cash deposit'
    )
    balance_cash_amount = fields.Float(
        related='cash_statement_id.balance_cash_amount',
        string='Balance Amount'
    )

    def action_deposit_to_manager_account(self):
        self._create_journal_entry()


    def action_deposit_to_petty_cash_account(self):
        self._create_journal_entry()

    def _create_journal_entry(self):
        '''
            create journal entry for Cash Amounts to Manager Account
        '''
        for rec in self:
            if not rec.cash_statement_id.pos_config_id:
                raise ValidationError("Terminal not Selected.")

            if rec.is_manager_deposit:
                if not rec.cash_statement_id.pos_config_id.manager_account_id:
                    raise ValidationError("Please Add Manager Account.")

                if rec.manager_amount <= 0 or rec.manager_amount > rec.balance_cash_amount:
                    raise ValidationError("Kindly recheck Deposit Amount.")
            if rec.is_petty_cash_deposit:
                if not rec.cash_statement_id.pos_config_id.petty_cash_account_id:
                    raise ValidationError("Please Add Petty Cash Account.")

                if rec.petty_cash_amount <= 0 or rec.petty_cash_amount > rec.balance_cash_amount:
                    raise ValidationError("Kindly recheck Deposit Amount.")

            if not rec.cash_statement_id.company_id.pos_cash_statement_journal_id:
                raise ValidationError("Please Add Cash Statement Journal.")

            if not rec.cash_statement_id.pos_config_id.payment_method_ids.filtered('is_cash_count'):
                raise ValidationError("Please Add Cash Payment Method.")

            vals = {
                'move_type': 'entry',
                'date': rec.cash_statement_id.statement_date,
                'currency_id': rec.cash_statement_id.currency_id.id,
                'journal_id': rec.cash_statement_id.company_id.pos_cash_statement_journal_id.id,
                'company_id': rec.cash_statement_id.company_id.id,
                'ref': rec.cash_statement_id.name,
                'cash_statement_id': rec.cash_statement_id.id,
            }
            move = self.env['account.move'].create(vals)
            move.write({'line_ids': [(0, 0, line_vals) for line_vals in rec._prepare_move_line_default_vals()]})
            move.message_post(body='This move is created against Cash Statement.')
            move.action_post()

    def _prepare_move_line_default_vals(self):
        '''
            Prepare the dictionary to create the default account.move.lines for the cash statement.

            :return: A list of python dictionary to be passed to the account.move.line's 'create' method.
        '''
        if self.is_manager_deposit:
            deposit_amount = self.manager_amount
        if self.is_petty_cash_deposit:
            deposit_amount = self.petty_cash_amount
        amount = self.cash_statement_id.currency_id._convert(
            deposit_amount,
            self.cash_statement_id.company_id.currency_id,
            self.cash_statement_id.company_id,
            fields.Datetime.now(),
        )
        currency_id = self.cash_statement_id.currency_id.id

        # Compute a default label to set on the journal items.
        liquidity_line_name = ''.join(x[1] for x in self._get_entry_default_display_name_list())
        counterpart_line_name = ''.join(x[1] for x in self._get_entry_default_display_name_list())

        if self.is_manager_deposit:
            deposit_account_id = self.cash_statement_id.pos_config_id.manager_account_id.id
        if self.is_petty_cash_deposit:
            deposit_account_id = self.cash_statement_id.pos_config_id.petty_cash_account_id.id
        terminal_cash_account_id = self.cash_statement_id.pos_config_id.payment_method_ids.filtered('is_cash_count').journal_id.default_account_id.id
        analytic_account_id = False
        if self.cash_statement_id.pos_config_id.analytic_account_id:
            analytic_account_id = {self.cash_statement_id.pos_config_id.analytic_account_id.id : 100}
        line_vals_list = [
            # Liquidity line.
            {
                'name': liquidity_line_name,
                'date_maturity': fields.Datetime.now(),
                'amount_currency': -(deposit_amount),
                'currency_id': currency_id,
                'debit': 0.0,
                'credit': amount,
                'account_id': terminal_cash_account_id,
                'analytic_distribution': analytic_account_id,
                'is_cash_statement_line': True,
                'is_manager_account_line': False,
                'pos_config_id': self.cash_statement_id.pos_config_id.id,
                'pos_session_id': self.cash_statement_id.pos_session_id.id
            },
            # Receivable / Payable.
            {
                'name': counterpart_line_name,
                'date_maturity': fields.Datetime.now(),
                'amount_currency': deposit_amount,
                'currency_id': currency_id,
                'debit': amount,
                'credit': 0.0,
                'account_id': deposit_account_id,
                'is_cash_statement_line': True,
                'is_manager_account_line': True,
                'pos_config_id': self.cash_statement_id.pos_config_id.id,
                'pos_session_id': self.cash_statement_id.pos_session_id.id
            },
        ]
        return line_vals_list

    def _get_entry_default_display_name_list(self):
        """
            Hook allowing custom values when constructing the default label to set on the pdc journal items.
        """
        self.ensure_one()
        reason = ''
        if self.is_manager_deposit:
            deposit_amount = self.manager_amount
            reason = self.manager_reason
        if self.is_petty_cash_deposit:
            deposit_amount = self.petty_cash_amount
            reason = self.petty_cash_reason
        values = [
            ('label', _('%s') % self.cash_statement_id.name),
            ('sep', ' '),
            ('sep', 'Against'),
            ('sep', ' '),
            ('sep', '%s' % self.cash_statement_id.pos_config_id.name),
            ('sep', ' '),
            ('amount', formatLang(self.env, deposit_amount, currency_obj=self.cash_statement_id.currency_id)),
            ('sep', ' - '),
            ('date', format_date(self.env, fields.Date.to_string(fields.Datetime.now())))
        ]
        if reason:
            values.append(('sep', ' - Reason - '))
            values.append(('sep', reason))
        return values

