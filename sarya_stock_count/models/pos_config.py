# -*- coding: utf-8 -*-
from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    stock_count_approve_manager_ids = fields.Many2many(
        comodel_name='hr.employee',
        string='Stock Count Approve Managers'
    )
