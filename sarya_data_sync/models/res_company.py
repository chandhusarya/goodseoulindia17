# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    pos_cash_statement_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Cash Statement Journal',
        check_company=True
    )
    pos_bank_transfer_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Cash Statement Journal',
        check_company=True
    )