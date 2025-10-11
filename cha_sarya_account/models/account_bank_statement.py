# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    incoming_receipt = fields.Many2one('account.account', string='Incoming Control Account')
    outgoing_payments = fields.Many2one('account.account', string='Outgoing Control Account')

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        for statement in self:
            journal_id = statement.journal_id
            incoming_receipt = False
            for method in journal_id.inbound_payment_method_line_ids:
                if method.payment_account_id:
                    incoming_receipt = method.payment_account_id.id
            statement.incoming_receipt = incoming_receipt
            outgoing_payments = False
            for method in journal_id.outbound_payment_method_line_ids:
                if method.payment_account_id:
                    outgoing_payments = method.payment_account_id.id
            statement.outgoing_payments = outgoing_payments

    def action_auto_match_entries(self):

        if not self.incoming_receipt:
            raise UserError(_("Please incoming receipt control account"))
        if not self.outgoing_payments:
            raise UserError(_("Please outgoing payments control account"))

        auto_matched_mv_line_ids = []
        for line in self.line_ids:
            if not line.is_reconciled:
                line.auto_matched_entry = False
                line.auto_matched_entry_move = False

        for line in self.line_ids:
            if not line.is_reconciled:
                move_line_search = [('date', '=', line.date), ('move_id.state', '=', 'posted')]
                if line.amount > 0.0001:
                    move_line_search.append(('account_id', '=', self.incoming_receipt.id))
                    move_line_search.append(('debit', '=', line.amount))
                if line.amount < 0:
                    move_line_search.append(('account_id', '=', self.outgoing_payments.id))
                    move_line_search.append(('credit', '=', line.amount * -1))
                move_lines = self.env['account.move.line'].search(move_line_search)
                print("line.amount ==>> ", line.amount)
                for move_line in move_lines:
                    if move_line.id not in auto_matched_mv_line_ids and move_line.amount_residual != 0:
                        print("amount_residual ==>> ", move_line.amount_residual)
                        line.auto_matched_entry = move_line.id
                        line.auto_matched_entry_move = move_line.move_id.id
                        auto_matched_mv_line_ids.append(move_line.id)
                        break

    def reconcile_matched_entries(self):
        for line in self.line_ids:
            if not line.is_reconciled:
                line.reconcile_matched_entries()

class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    auto_matched_entry = fields.Many2one('account.move.line', string='Auto Matched Move Line')
    auto_matched_entry_move = fields.Many2one('account.move', string='Auto Matched')

    def manual_bank_reconcile_bank_statements(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'bank_statement_reconciliation_view',
            'context': {'statement_line_ids': self.ids, 'company_ids': self.mapped('company_id').ids},
        }

    def reconcile_matched_entries(self):

        for line in self:
            if line.auto_matched_entry and line.auto_matched_entry.amount_residual != 0:

                balance = line.auto_matched_entry.amount_residual
                balance = balance * -1
                name = ""
                if line.auto_matched_entry_move.name:
                    name = line.auto_matched_entry_move.name
                else:
                    raise UserError(_('Please check entry with id : %s' % str(line.auto_matched_entry_move.id)))

                if line.auto_matched_entry.name:
                    name = name + " : " + line.auto_matched_entry.name
                else:
                    raise UserError(_('Please check entry with id : %s' % str(line.auto_matched_entry_move.id)))

                datum = [{
                    'name': name,
                    'balance': balance,
                    # 'analytic_tag_ids': [[6, None, []]],
                    'id': line.auto_matched_entry.id,
                    'currency_id': line.auto_matched_entry.currency_id.id}]
                line.reconcile(datum)