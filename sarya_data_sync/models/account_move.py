# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    cash_statement_id = fields.Many2one(
        comodel_name='cash.statement',
        string='Cash Statement',
        copy=False
    )
