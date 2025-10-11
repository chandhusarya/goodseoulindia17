# -*- coding: utf-8 -*-

from odoo import models, fields, _, api
from odoo.exceptions import UserError

class AccountIncoterms(models.Model):
    _inherit = 'account.incoterms'

    allowed_landed_costs = fields.Many2many('product.product', 'account_incoterm_product_rel',
                                    string="Allowed Landed Costs", domain="[('landed_cost_ok', '=', True)]")