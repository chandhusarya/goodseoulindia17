# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, SUPERUSER_ID


class StockLocation(models.Model):
    _inherit = 'stock.location'

    address_id = fields.Many2one('res.partner', string='Address')