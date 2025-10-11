'''
Created on Nov 18, 2019

@author: Zuhair Hammadi
'''
from odoo import models, fields
from . import COST_LEVEL_SELECTION

class ProductCategory(models.Model):
    _inherit = 'product.category'
    
    property_cost_level = fields.Selection(COST_LEVEL_SELECTION, string='Costing Level', company_dependent=True, copy=True)