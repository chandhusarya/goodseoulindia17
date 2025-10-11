from odoo import fields, models, api


class StockCheckPaln(models.Model):
    _name = 'stock.check.plan'
    _description = 'Stock Check Plan'

    name = fields.Char(required=1)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    products_ids = fields.Many2many('product.product', string='Products')
