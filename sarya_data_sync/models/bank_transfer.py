# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import ValidationError


class BankTransfer(models.Model):
    _name = 'bank.transfer'
    _description = 'Bank Transfer'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(
        string="Name",
        required=True,
        default='New',
        copy=False
    )
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today
    )
    pos_config_ids = fields.Many2many(
        comodel_name='pos.config',
        string="POS Terminals",
        help="POS Terminals",
        copy=False
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='company_id.currency_id',
        string="Company Currency"
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('lines_computed', 'Lines Computed'),
            ('done', 'Done'),
            ('cancel', 'Cancel'),
        ],
        string='Status',
        required=True,
        copy=False,
        default='draft',
        tracking=True
    )
    bank_transfer_line_ids = fields.One2many(
        comodel_name='bank.transfer.line',
        inverse_name='bank_transfer_id',
        string='Lines'
    )
    total = fields.Float(string='Total', compute='_compute_total')
    move_id = fields.Many2one('account.move', string='Journal Entry', copy=False)

    @api.depends('bank_transfer_line_ids.amount')
    def _compute_total(self):
        """ Compute the total amount of the bank transfer lines """
        for rec in self:
            rec.total = sum(line.amount for line in rec.bank_transfer_line_ids)

    @api.model
    def create(self, vals):
        # Step 1: If the name is still 'New', assign a sequence-generated name
        vals['name'] = self.env['ir.sequence'].next_by_code('bank.transfer.sequence') or 'New'

        # Step 2: Call the original create method with updated values
        return super(BankTransfer, self).create(vals)

    def action_compute_cash_statements_line(self):
        print('&&&&&&&&&&&&&&')
        for rec in self.pos_config_ids:
            domain = [
                ('balance_amount', '>', 0),
                ('pos_config_id', '=', rec.id),
                ('state', '=', 'deposit')
            ]
            lines = self.env['cash.statement'].sudo().search(domain)

    def action_compute_cash_statements_line(self):
        """ Recompute cash statement lines """
        for rec in self:
            # Step 1: Clear old lines
            rec.bank_transfer_line_ids.unlink()

            # Step 2: Your logic to compute new lines
            new_lines = []
            for pos in rec.pos_config_ids:
                domain = [
                    ('balance_amount', '>', 0.0),
                    ('pos_config_id', '=', pos.id),
                    ('state', '=', 'deposit')
                ]
                lines = self.env['cash.statement'].search(domain)
                for line in lines:
                    if line.balance_amount > 0.0:
                        new_lines.append((0, 0, {
                            'pos_config_id': line.pos_config_id.id,
                            'pos_session_id': line.pos_session_id.id,
                            'amount': line.balance_amount,
                            'cash_statement_id': line.id,
                        }))

            # Step 3: Add new lines
            rec.write({'bank_transfer_line_ids': new_lines})

            # Step 4: Update state
            rec.state = 'lines_computed'
    def action_deposit_to_bank(self):
        for rec in self:
            journal = rec.company_id.pos_bank_transfer_journal_id
            if not journal:
                raise ValidationError("Please configure POS Bank Transfer Journal in Company settings.")

            debit_account = False
            for method in journal.inbound_payment_method_line_ids:
                if method.payment_account_id:
                    debit_account = method.payment_account_id
            if not debit_account:
                raise ValidationError("The journal %s does not have a outstanding receipt account." % journal.display_name)

            move_vals = {
                'ref': rec.name,
                'journal_id': journal.id,
                'date': rec.date,
                'line_ids': []
            }

            total_amount = 0.0
            line_vals = []

            # 🔹 Group by pos_config_id and sum
            grouped_amounts = {}
            for line in rec.bank_transfer_line_ids:
                if line.cash_statement_id.balance_amount < 0:
                    raise ValidationError("Cannot transfer negative balance amounts from cash statements %s." % line.cash_statement_id.name)
                if line.amount > 0:
                    grouped_amounts.setdefault(line.pos_session_id, 0.0)
                    grouped_amounts[line.pos_session_id] += line.amount

            # 🔹 Create credit lines per POS config (aggregated)
            for session, amount in grouped_amounts.items():
                manager_account = session.config_id.manager_account_id
                if not manager_account:
                    raise ValidationError("Manager account not configured for POS %s" % session.config_id.display_name)
                analytic_account_id = False
                if session.config_id.analytic_account_id:
                    analytic_account_id = {session.config_id.analytic_account_id.id: 100}

                line_vals.append((0, 0, {
                    'account_id': manager_account.id,
                    'credit': amount,
                    'analytic_distribution': analytic_account_id,
                    'debit': 0.0,
                    'name': 'POS Transfer - %s - %s' % (session.config_id.display_name or '', session.name or ''),
                }))
                total_amount += amount

            if total_amount == 0:
                raise ValidationError("No valid transfer amount found.")

            # 🔹 Add Debit line (balancing entry)
            line_vals.append((0, 0, {
                'account_id': debit_account.id,
                'debit': total_amount,
                'credit': 0.0,
                'name': 'POS Bank Transfer',
            }))

            move_vals['line_ids'] = line_vals

            move = self.env['account.move'].create(move_vals)
            move.action_post()

            rec.move_id = move.id
            rec.state = 'done'

    def action_cancel(self):
        """ Cancel the bank transfer """
        for rec in self:
            if rec.state not in ['draft', 'lines_computed']:
                raise ValidationError("You can only cancel transfers in draft or lines computed state.")
            rec.state = 'cancel'
            rec.bank_transfer_line_ids.unlink()

    def action_reset(self):
        """ Reset the bank transfer to draft state """
        for rec in self:
            if rec.state not in ['cancel', 'lines_computed']:
                raise ValidationError("You can only reset transfers in cancel or lines computed state.")
            rec.state = 'draft'
            rec.bank_transfer_line_ids.unlink()
