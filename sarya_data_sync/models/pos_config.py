# -*- coding: utf-8 -*-
from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    outlet_terminal_code = fields.Char(
        string='Outlet Terminal Code',
        copy=False
    )
    manager_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Manager Account',
        copy=False
    )
    petty_cash_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Petty Cash Account',
        copy=False
    )
    petty_cash_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Petty Cash Journal',
        copy=False
    )
