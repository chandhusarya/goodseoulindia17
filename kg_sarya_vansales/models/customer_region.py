# -*- coding: utf-8 -*-

from odoo import models, fields


class Region(models.Model):
    _inherit = 'customer.region'

    route_id = fields.Many2one('user.route')
