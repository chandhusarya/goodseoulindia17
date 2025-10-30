from odoo import models, fields, api

class MrpBomComponentLine(models.Model):
    _name = 'mrp.bom.component.line'
    _description = 'Flattened BOM Component Line'

    bom_id = fields.Many2one('mrp.bom', string='Top-Level BOM')
    product_id = fields.Many2one('product.product', string='Component Product')
    quantity = fields.Float(string='Quantity')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    parent_id = fields.Many2one('mrp.bom.component.line', string='Parent Component')
    level = fields.Integer(string='Level', help='Level in BOM tree')
    bom_cost = fields.Float(string='BOM Cost')
    prod_cost = fields.Float(string='Product Cost')
    route_type = fields.Char(string='Route Type')
    route_name = fields.Char(string='Route Name')
    link_id = fields.Integer(string='Linked Product Template')
