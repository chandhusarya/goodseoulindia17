from odoo import models, fields


class ProductPricelistDtls(models.Model):
    _inherit = "product.pricelist"

    rebate_ids = fields.Many2many('rebate.master', string='Rebate')
