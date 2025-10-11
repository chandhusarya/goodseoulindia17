# -*- coding: utf-8 -*-
from odoo import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    requested_user_id = fields.Many2one('res.users', 'Requested By', copy=False,
                                        help="Choose salesman who requested for loading/unloading stock.")
    request_date = fields.Date('Requested On', copy=False)
