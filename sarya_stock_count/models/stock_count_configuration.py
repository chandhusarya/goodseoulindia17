# -*- coding: utf-8 -*-
from odoo import fields, models


class StockCountConfig(models.Model):
    _name = "stock.count.config"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _description = "Stock Count Conf"
    _order = "id desc"

    _sql_constraints = [('name_unique', 'unique (name)', "this name already exists")]

    name = fields.Char(
        string='Stock Count Configuration Name',
        required=True,
        copy=False
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        readonly=True,
        default=lambda self: self.env.company
    )
    pos_config_id = fields.Many2one(
        comodel_name='pos.config',
        string='POS Outlet',
        tracking=True,
    )
    allowed_product_ids = fields.Many2many(
        comodel_name='product.product',
        string="Products"
    )
