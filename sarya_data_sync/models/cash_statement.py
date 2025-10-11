# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class CashStatement(models.Model):
    _name = 'cash.statement'
    _description = 'Cash Statement'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(
        string="Name",
        required=True,
        readonly=True,
        default='New',
        copy=False
    )
    amount = fields.Float(
        string='Amount'
    )
    reason = fields.Char(
        string='Reason'
    )
    outlet_code = fields.Char(
        string='Outlet Code'
    )
    outlet_terminal_code = fields.Char(
        string='Outlet Terminal Code'
    )
    pos_config_id = fields.Many2one(
        comodel_name='pos.config',
        string="Outlet"
    )
    pos_session_id = fields.Many2one(
        comodel_name='pos.session',
        string="Session",
        required=True
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        copy=False
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='company_id.currency_id',
        string="Company Currency"
    )
    state = fields.Selection(
        selection=[
            ('on_hand', 'On Hand'),
            ('deposit', 'Deposit'),
            ('cancel', 'Cancel'),
        ],
        compute='_compute_is_deposit_completed',
        string='Status',
        required=True,
        readonly=True,
        copy=False,
        default='on_hand',
        tracking=True
    )
    local_rec_id = fields.Integer(
        string='Local Record Id',
        copy=False
    )
    journal_entry_count = fields.Integer(
        compute='_compute_journal_entry_count'
    )
    statement_date = fields.Datetime(
        string='Statement Date',
        related='pos_session_id.stop_at'
    )
    balance_cash_amount = fields.Float(
        string='Balance Cash Amount',
        compute='_compute_balance_cash_amount'
    )
    is_deposit_completed = fields.Boolean(
        string='Is Deposit Completed?',
        compute='_compute_is_deposit_completed'
    )
    balance_amount = fields.Float(
        string='Balance Amount',
        compute='_compute_balance_amount'
    )
    bank_transfer_line_ids = fields.One2many(
        comodel_name='bank.transfer.line',
        inverse_name='cash_statement_id',
        string='Transfer Lines'
    )

    @api.depends('bank_transfer_line_ids.amount', 'amount')
    def _compute_balance_amount(self):
        for record in self:
            record.balance_amount = round(record.amount - sum(record.bank_transfer_line_ids.filtered(lambda b: b.bank_transfer_id.state != 'cancel').mapped('amount')), 2)

    @api.depends('balance_cash_amount')
    def _compute_is_deposit_completed(self):
        for rec in self:
            if rec.balance_cash_amount == 0:
                rec.is_deposit_completed = True
                rec.state = 'deposit'
            else:
                rec.is_deposit_completed = False
                rec.state = 'on_hand'

    @api.depends('amount')
    def _compute_balance_cash_amount(self):
        for rec in self:
            domain = [
                ('move_id.cash_statement_id', '=', rec.id),
                '|',
                ('is_manager_account_line', '=', True),
                ('is_petty_cash_account_line', '=', True),
                ('parent_state', '=', 'posted')
            ]
            lines = self.env['account.move.line'].sudo().search(domain)
            rec.balance_cash_amount = rec.amount - sum(lines.mapped('balance'))

    def _compute_journal_entry_count(self):
        cash_statement_datas = self.env['account.move']._read_group([('cash_statement_id', 'in', self.ids)], ['cash_statement_id'], ['__count'])
        account_move_data = {cash.id: count for cash, count in cash_statement_datas}
        for cash in self:
            cash.journal_entry_count = account_move_data.get(cash.id, 0)

    def action_open_cash_deposit_manager_account_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Cash Deposit To Manager Account"),
            'view_mode': 'form',
            'res_model': 'cash.deposit.wizard',
            'target': 'new',
            'context': {'default_cash_statement_id': self.id, 'default_is_manager_deposit': True}
        }

    def action_open_cash_deposit_petty_cash_account_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Cash Deposit To Petty Cash Account"),
            'view_mode': 'form',
            'res_model': 'cash.deposit.wizard',
            'target': 'new',
            'context': {'default_cash_statement_id': self.id, 'default_is_petty_cash_deposit': True}
        }

    def action_view_journal_entry(self):
        """ Return the action for the views of the journal entry linked to the transaction.

        Note: self.ensure_one()

        :return: The action
        :rtype: dict
        """
        self.ensure_one()
        return {
            'name': _('journal Entry'),
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
            'domain': [('cash_statement_id', '=', self.ids)],
            'context': {'create': False}
        }