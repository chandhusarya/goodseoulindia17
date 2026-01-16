from odoo import api, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero

class StockMove(models.Model):
    _inherit = "stock.move"

    def _create_out_svl(self, forced_quantity=None):

        #Find warehouse id from From location on move
        #Cannot mix move from different warehouses
        warehouse_id = False
        for move in self:
            if warehouse_id and warehouse_id != move.location_id.warehouse_id.id:
                raise UserError("Cannot process moves from different warehouses together. Please check locations in the moves")
            warehouse_id = move.location_id.warehouse_id.id

        if not warehouse_id:
            raise UserError("Cannot determine warehouse from source location. Please check locations in the moves")

        moves_with_ctx = self.with_context(warehouse_id_valuation=warehouse_id)

        return super(StockMove, moves_with_ctx)._create_out_svl(forced_quantity=forced_quantity)

    def _action_done(self, cancel_backorder=False):
        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
        #Check the move is internal transfer and location and destination location belong to different warehouses
        for move in self:
            if move.location_id.usage == 'internal' and move.location_dest_id.usage == 'internal':
                src_wh = move.location_id.warehouse_id
                dest_wh = move.location_dest_id.warehouse_id
                if src_wh and dest_wh and src_wh != dest_wh:
                    move._create_internal_wh_svl()
        return res

    def _get_internal_move_lines(self):
        """ Returns the `stock.move.line` records of `self` considered as outgoing. It is done thanks
        to the `_should_be_valued` method of their source and destionation location as well as their
        owner.

        :returns: a subset of `self` containing the outgoing records
        :rtype: recordset
        """
        res = self.env['stock.move.line']
        for move_line in self.move_line_ids:
            src_wh = move_line.location_id.warehouse_id
            dest_wh = move_line.location_dest_id.warehouse_id
            if src_wh and dest_wh and src_wh != dest_wh:
                res |= move_line
        return res


    def _prepare_common_svl_vals_internal_wh(self):
        """When a `stock.valuation.layer` is created from a `stock.move`, we can prepare a dict of
        common vals.

        :returns: the common values when creating a `stock.valuation.layer` from a `stock.move`
        :rtype: dict
        """
        self.ensure_one()
        return {
            'stock_move_id': self.id,
            'company_id': self.company_id.id,
            'product_id': self.product_id.id,
            'description': self.reference and '%s - %s' % (self.reference, self.product_id.name) or self.product_id.name,
        }



    def _create_internal_wh_svl(self, forced_quantity=None):
        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circunstances, the quantity to value is different than
            the initial demand of the move (Default value = None)
        """
        svl_vals_list = []
        for move in self:
            move = move.with_company(move.company_id)
            valued_move_lines = move._get_internal_move_lines()
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.quantity, move.product_id.uom_id)
            if float_is_zero(forced_quantity or valued_quantity, precision_rounding=move.product_id.uom_id.rounding):
                continue
            svl_vals = move.product_id._prepare_intenal_wh_svl_vals(forced_quantity or valued_quantity,
                                                                    move.company_id,
                                                                    move.location_id.warehouse_id.id,
                                                                    move.location_dest_id.warehouse_id.id)
            svl_vals.update(move._prepare_common_svl_vals_internal_wh())
            if forced_quantity:
                svl_vals['description'] = 'Correction of %s (modification of past move)' % (move.picking_id.name or move.name)
            svl_vals['description'] += svl_vals.pop('rounding_adjustment', '')
            svl_vals_list.append(svl_vals)

        return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)




