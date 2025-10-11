# -*- coding: utf-8 -*-
from odoo import models, fields


class ProductSupplierInfoInherit(models.Model):
    _inherit = "product.supplierinfo"

    discount_1 = fields.Float(string='Disc 1')
    discount_2 = fields.Float(string='Disc 2')
