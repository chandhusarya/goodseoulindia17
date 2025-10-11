'''
Created on Oct 12, 2021

@author: Zuhair Hammadi
'''
from odoo import models, api

class StockQuant(models.Model):
    _inherit = 'stock.quant'
    
    @api.depends('company_id', 'location_id', 'owner_id', 'product_id', 'quantity')
    def _compute_value(self):
        super(StockQuant, self)._compute_value()
        for record in self:
            if record.product_id.cost_level == 'lot':
                svls = self.env['stock.valuation.layer'].sudo().search([('product_id','=', record.product_id.id), ('company_id','=', record.company_id.id),('lot_id','=', record.lot_id.id), ('remaining_qty','>',0)])
                total_value = 0
                total_qty = 0
                for svl in svls:
                    total_value += svl.remaining_value
                    total_qty += svl.remaining_qty
                unit_value = total_qty and total_value / total_qty or 0
                #record.quantity = total_qty
                record.value = unit_value * record.quantity






    def correct_stock_quant(self):

        qunats = self.env['stock.quant'].sudo().search([])

        for q in qunats:

            out_move_domain = [('location_id', '=', q.location_id.id),
                               ('state', '=', 'done'),
                        ('lot_id', '=', q.lot_id.id),
            '|',
                ('package_id', '=', q.package_id.id),
                ('result_package_id', '=', q.package_id.id),
            ]

            in_move_domain = [('location_dest_id', '=', q.location_id.id),
                               ('state', '=', 'done'),
                        ('lot_id', '=', q.lot_id.id),
                    '|',
                ('package_id', '=', q.package_id.id),
                ('result_package_id', '=', q.package_id.id),
            ]

            out_moves = self.env['stock.move.line'].sudo().search(out_move_domain)
            in_moves = self.env['stock.move.line'].sudo().search(in_move_domain)

            quantity = 0
            for in_m in in_moves:
                quantity += in_m.quantity
            for out_m in out_moves:
                quantity -= out_m.quantity

            q.quantity = quantity
            q._compute_value()

