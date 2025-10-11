# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class PosConfig(models.Model):
    _inherit = 'pos.config'

    show_product_cost = fields.Boolean(string="Show Product Cost")
    restrict_sale_below_cost = fields.Boolean(string="Restrict Sale Below Cost")

