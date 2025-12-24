# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    is_foc_pricelist = fields.Boolean(
        string='Is FOC Pricelist?',
        default=False,
        copy=False,
        tracking=True
    )
