# -*- coding: utf-8 -*-
from odoo import fields, models


class BankStatementLine(models.Model):
    _name = 'bank.transfer.line'
    _description = 'Bank Transfer Lines'
    _rec_name = 'bank_transfer_id'

    bank_transfer_id = fields.Many2one(
        comodel_name='bank.transfer',
        string='Bank Transfer'
    )
    account_move_line_id = fields.Many2one(
        comodel_name='account.move.line',
        string='Move Line'
    )
    sequence = fields.Integer(
        string="Sequence"
    )
    pos_config_id = fields.Many2one(
        comodel_name='pos.config',
        string='Terminal'
    )
    pos_session_id = fields.Many2one(
        comodel_name='pos.session',
        string='Session'
    )
    amount = fields.Float(
        string='Amount'
    )
    cash_statement_id = fields.Many2one('cash.statement', string='Cash Statement')