from odoo import fields, models, api


class MRPBomItem(models.Model):
    _name = 'mrp.bom.item'
    _description = 'BOM Item'

    name = fields.Char()
    parent_id = fields.Many2one('mrp.bom.item', string='Parent')
