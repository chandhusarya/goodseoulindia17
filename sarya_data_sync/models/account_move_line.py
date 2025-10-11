# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_cash_statement_line = fields.Boolean(
        string='Cash Statement Line',
        default=False
    )
    is_manager_account_line = fields.Boolean(
        string='Manager Account Line',
        default=False
    )
    is_petty_cash_account_line = fields.Boolean(
        string='Petty Cash Account Line',
        default=False
    )
    pos_config_id = fields.Many2one(
        comodel_name='pos.config',
        string='Terminal',
        readonly=True,
        copy=False
    )
    pos_session_id = fields.Many2one(
        comodel_name='pos.session',
        string='Session',
        readonly=True,
        copy=False
    )