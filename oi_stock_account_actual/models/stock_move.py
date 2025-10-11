'''
Created on Nov 18, 2019

@author: Zuhair Hammadi
'''
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round

class StockMove(models.Model):
    _inherit = "stock.move"
    
    lot_id = fields.Many2one('stock.lot', 'Lot/Serial Number', compute = '_calc_lot_id', store = True)


    def _create_extra_move(self):
        """ If the quantity done on a move exceeds its quantity todo, this method will create an
        extra move attached to a (potentially split) move line. If the previous condition is not
        met, it'll return an empty recordset.

        The rationale for the creation of an extra move is the application of a potential push
        rule that will handle the extra quantities.
        """
        extra_move = self
        rounding = self.product_uom.rounding
        if float_is_zero(self.product_uom_qty, precision_rounding=rounding):
            return self
        # moves created after the picking is assigned do not have `product_uom_qty`, but we shouldn't create extra moves for them

        if float_compare(self.quantity, self.product_uom_qty, precision_rounding=rounding) > 0 and False:
            # create the extra moves
            extra_move_quantity = float_round(
                self.quantity - self.product_uom_qty,
                precision_rounding=rounding,
                rounding_method='HALF-UP')
            extra_move_vals = self._prepare_extra_move_vals(extra_move_quantity)
            self = self.with_context(avoid_putaway_rules=True, extra_move_mode=True)
            extra_move = self.copy(default=extra_move_vals)
            return extra_move.with_context(merge_extra=True, do_not_unreserve=True)._action_confirm(merge_into=self)
        return self

    @api.depends('move_line_ids.lot_id')
    def _calc_lot_id(self):
        for record in self:
            lot_id = record.mapped('move_line_ids.lot_id')
            record.lot_id = len(lot_id) == 1 and lot_id.id
    
    def _prepare_common_svl_vals(self):
        vals = super(StockMove, self)._prepare_common_svl_vals()
        if self.product_id.cost_level == 'lot' and len(self.move_line_ids.lot_id) == 1:
            vals.update({
                'lot_id' : self.move_line_ids.lot_id.id
                })
        return vals
    
    def _create_out_svl(self, forced_quantity=None):
        move_ids = self.filtered(lambda move : move.product_id.cost_level == 'lot')
        svl_ids = super(StockMove, self - move_ids)._create_out_svl(forced_quantity = forced_quantity)
        svl_ids += move_ids._create_out_svl_lot(forced_quantity = forced_quantity)
        return svl_ids
    

    def _create_out_svl_lot(self, forced_quantity=None):
        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circunstances, the quantity to value is different than
            the initial demand of the move (Default value = None)
        """
        svl_vals_list = []
        for move in self:
            move = move.with_context(force_company=move.company_id.id)
            valued_move_lines = move._get_out_move_lines()
            print("valued_move_lines", valued_move_lines)
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.quantity, move.product_id.uom_id)
            if float_is_zero(forced_quantity or valued_quantity, precision_rounding=move.product_id.uom_id.rounding):
                continue
            print("==============move.product_id", move.product_id.name)
            print("move.lot_id", move.lot_id)
            svl_vals = move.product_id._prepare_out_svl_vals_lot(forced_quantity or valued_quantity, move.company_id, move.lot_id)
            svl_vals.update(move._prepare_common_svl_vals())
            if forced_quantity:
                svl_vals['description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
            svl_vals['description'] += svl_vals.pop('rounding_adjustment', '')
            svl_vals_list.append(svl_vals)
        return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)


    def _get_price_unit(self):
        """ Returns the unit price to value this stock move """
        self.ensure_one()
        # print("======================================================================")
        # print("======================================================================")
        # print("======================================================================")
        # print("Product ID", self.product_id.name)
        # print("Product Price", self.price_unit)
        # print("Product Lot", self.lot_id)
        price_unit = self.price_unit
        precision = self.env['decimal.precision'].precision_get('Product Price')



        if float_is_zero(price_unit, precision):

            price_unit = self.get_cost_price_from_inventory_valutaion()

        if float_is_zero(price_unit, precision):
            price_unit = self.lot_id.final_cost

        if float_is_zero(price_unit, precision):
            price_unit = self.product_id.manual_cost_for_zero_cost_item

        #Check of it local purchase order
        if float_is_zero(price_unit, precision) and self.product_id and self.picking_id:
            local_po_line = self.env['local.purchase.line'].search([('product_id', '=', self.product_id.id),
                                                                    ('local_purchase_id.picking_id', '=', self.picking_id.id)
                                                                    ], limit=1)
            if local_po_line:
                price_unit = local_po_line.unit_price
        print("Product", self.product_id.name)
        print("precision", precision)
        print("Price Unit", price_unit)



        if float_is_zero(price_unit, precision):
            # ffffffffffffffffffffffffffffff
            error_text = "222222222 Couldn't find correct costing for lot %s, please apply sku wise costing in product master of -> %s" % (self.lot_id.name, self.product_id.name)
            raise UserError(_(error_text))

        return price_unit

    def get_cost_price_from_inventory_valutaion(self):
        """CHANDHU :: Logic for getting cost price is wrong, It was taking sale price for the stock valuation also"""
        self.ensure_one()
        price_unit = 0

        #Getting Puchase Value
        stock_valuation = self.env['stock.valuation.layer'].sudo().with_context(active_test=False).search([
            ('product_id', '=', self.product_id.id),
            ('company_id', '=', self.company_id.id),
            ('lot_id', '=', self.lot_id.id)], order='create_date, id')
        if stock_valuation:
            purchase_stock_valuation = stock_valuation[0]
            value = purchase_stock_valuation.value
            quantity = purchase_stock_valuation.quantity

            if not purchase_stock_valuation.stock_move_id:
                return price_unit
            if not purchase_stock_valuation.stock_move_id.origin:
                return price_unit
            if 'P0' not in purchase_stock_valuation.stock_move_id.origin and 'LP' not in purchase_stock_valuation.stock_move_id.origin:
                print("Inside ----------")
                return price_unit

            # Adding landed cost to Purchase Value
            domain = [
                ('company_id', '=', self.company_id.id),
                ('product_id', '=', self.product_id.id),
                ('lot_id', '=', self.lot_id.id),
                ('quantity', '=', 0),
                ('unit_cost', '=', 0),
                ('create_date', '>=', purchase_stock_valuation.create_date),
                ('stock_landed_cost_id', '!=', False)
            ]
            all_candidates = self.env['stock.valuation.layer'].sudo().search(domain)
            for candidate in all_candidates:
                value += candidate.value

            #Getting unit price by dividing total value and total quantity
            if quantity > 0.001:
                price_unit = value/quantity
        return price_unit
