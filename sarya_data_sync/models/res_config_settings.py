# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_cash_statement_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Cash Statement Journal',
        readonly=False,
        check_company=True,
        related='company_id.pos_cash_statement_journal_id',
        help='Cash Statement Journal.'
    )
    pos_bank_transfer_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Bank Transfer Journal',
        readonly=False,
        check_company=True,
        related='company_id.pos_bank_transfer_journal_id',
        help='Bank Transfer Journal.'
    )