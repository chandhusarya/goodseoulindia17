from odoo import api, fields, models

class StockValuationLayer(models.Model):
    _inherit = "stock.valuation.layer"

    force_warehouse = fields.Many2one('stock.warehouse', string="Force Warehouse")
    warehouse_id = fields.Many2one('stock.warehouse', string="Receipt WH", compute='_compute_warehouse_id',
                                   search='_search_warehouse_id')

    def _search_warehouse_id(self, operator, value):
        layer_ids = self.search([
            '|',
            ('stock_move_id.location_dest_id.warehouse_id', operator, value),
            '&',
            ('stock_move_id.location_id.usage', '=', 'internal'),
            ('stock_move_id.location_id.warehouse_id', operator, value),
        ]).ids
        return [('id', 'in', layer_ids)]

    def _compute_warehouse_id(self):
        for svl in self:
            if svl.force_warehouse:
                svl.warehouse_id = svl.force_warehouse.id
            else:
                if svl.stock_move_id.location_id.usage == "internal":
                    svl.warehouse_id = svl.stock_move_id.location_id.warehouse_id.id
                else:
                    svl.warehouse_id = svl.stock_move_id.location_dest_id.warehouse_id.id

    def _search_warehouse_id(self, operator, value):
        """
        Search helper for computed field warehouse_id.

        Mirrors _compute_warehouse_id logic:
          - If force_warehouse is set, use that.
          - Else, if source location is internal, use its warehouse.
          - Else, use destination warehouse.
        """
        Svl = self.env['stock.valuation.layer']

        force_warehouse_match = Svl.search([
            ('force_warehouse', operator, value),
        ]).ids

        location_id_match = Svl.search([
            ('force_warehouse', '=', False),
            ('stock_move_id.location_id.usage', '=', 'internal'),
            ('stock_move_id.location_id.warehouse_id', operator, value),
        ]).ids

        location_dest_id_match = Svl.search([
            ('force_warehouse', '=', False),
            ('stock_move_id.location_id.usage', '!=', 'internal'),
            ('stock_move_id.location_dest_id.warehouse_id', operator, value),
        ]).ids

        layer_ids = list(set(
            force_warehouse_match
            + location_id_match
            + location_dest_id_match
        ))

        # print("layer_ids ==>> ", layer_ids)

        return [('id', 'in', layer_ids)]

