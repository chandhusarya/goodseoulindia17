# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class StockMove(models.Model):
    _inherit = "stock.move"

    stock_count_id = fields.Many2one(
        comodel_name='stock.count',
        string='Stock Count Reference',
        index=True,
        ondelete='cascade'
    )