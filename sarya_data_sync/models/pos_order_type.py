# -*- coding: utf-8 -*-
from odoo import fields, models


class PosOrderType(models.Model):
    _name = 'pos.order.type'
    _description = 'Pos Order Type'

    name = fields.Char(
        string='Name',
        copy=False
    )
    img = fields.Image(
        string='Image',
        copy=False,
        max_width=200,
        max_height=200
    )
    is_home_delivery = fields.Boolean(
        string='Is Home Delivery?',
        copy=False
    )
    is_dine_in = fields.Boolean(
        string='Is Dine In?',
        copy=False
    )
    is_take_away = fields.Boolean(
        string='Is Take Away?',
        copy=False
    )

