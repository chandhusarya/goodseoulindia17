'''
Created on Nov 18, 2019

@author: Zuhair Hammadi
'''
from odoo import models, fields, api
from . import COST_LEVEL_SELECTION

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    property_cost_level = fields.Selection(COST_LEVEL_SELECTION, string='Costing Level', company_dependent=True, copy=True)
    cost_level = fields.Selection(COST_LEVEL_SELECTION, compute='_calc_cost_level', inverse='_set_lot_level')
    manual_cost_for_zero_cost_item = fields.Float("Manual Cost for Zero Cost Item", tracking=True)
    
    @api.depends('property_cost_level', 'categ_id.property_cost_level', 'tracking')
    def _calc_cost_level(self):
        for record in self:
            if record.tracking !='none' and record.type == 'product' and record.cost_method == 'fifo':
                record.cost_level = record.property_cost_level or record.categ_id.property_cost_level  
            else:
                record.cost_level = False          
    
    def _set_lot_level(self):
        for record in self:
            record.write({'property_lot_level' : record.lot_level})