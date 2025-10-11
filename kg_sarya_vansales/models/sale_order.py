# -*- coding: utf-8 -*-
from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    shift_id = fields.Many2one('user.shift', 'Shift', copy=False, )
    vehicle_id = fields.Many2one('user.vehicle', 'Vehicle', copy=False,
                                 help="Vehicle used to sell the products included in this sale order.")
