# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    account_analytic_id = fields.Many2one(
        comodel_name='account.analytic.account',
        related="session_id.account_analytic_id",
        copy=False,
        store=True,
        string='Analytic Account'
    )