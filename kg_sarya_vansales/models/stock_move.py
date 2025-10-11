# -*- coding: utf-8 -*-
from odoo import models,fields

class StockMove(models.Model):
    _inherit = 'stock.move'

    lot = fields.Many2one('stock.lot')
    sales_return_line_id = fields.Many2one('sales.return.form.line', string="Sales Return Line", copy=False)

    def _prepare_move_split_vals(self, qty):
        """overrides the function to inject pkg_demand and pkg_done while confirming picking without backorder."""
        vals = super(StockMove, self)._prepare_move_split_vals(qty)
        if self.product_packaging_id:
            vals.update({
                'pkg_demand': qty / self.product_packaging_id.qty,
                'pkg_done': 0.0,
            })
        return vals