from odoo import models, fields, _, api, SUPERUSER_ID, tools
from odoo.exceptions import ValidationError, UserError
from datetime import date



class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    shipment_ids = fields.Many2many('shipment.advice')
    is_customs_entry = fields.Boolean("Is customs entry")




    def get_valuation_lines(self):
        self.ensure_one()
        lines = []
        for move in self._get_targeted_move_ids():

            # it doesn't make sense to make a landed cost for a product that isn't set as being valuated in real time at real cost
            if move.product_id.cost_method not in ('fifo', 'average') or move.state == 'cancel' or not move.quantity:
                continue

            vals = {
                'product_id': move.product_id.id,
                'move_id': move.id,
                'quantity': move.quantity,
                'former_cost': sum(move.stock_valuation_layer_ids.mapped('value')),
                'weight': move.product_id.weight * move.quantity,
                'volume': move.product_id.volume * move.quantity
            }
            lines.append(vals)

        if not lines:
            target_model_descriptions = dict(self._fields['target_model']._description_selection(self.env))
            raise UserError(_("You cannot apply landed costs on the chosen %s(s). Landed costs can only be applied for products with FIFO or average costing method.", target_model_descriptions[self.target_model]))
        return lines

    @api.onchange('shipment_ids')
    def onchange_shipment_id(self):
        for landed_cost in self:
            if landed_cost.shipment_ids:
                pickings = []
                for shipment_id in landed_cost.shipment_ids.ids:
                    picking_ids = self.env['stock.picking'].search([('shipment_id', '=', shipment_id)])

                    for picking in picking_ids:
                        if picking.location_id.usage == 'supplier':
                            pickings.append(picking.id)
                landed_cost.write({'picking_ids': [(6, 0, pickings)]})


    def compute_landed_cost(self):
        AdjustementLines = self.env['stock.valuation.adjustment.lines']
        AdjustementLines.search([('cost_id', 'in', self.ids)]).unlink()

        towrite_dict = {}
        for cost in self.filtered(lambda cost: cost._get_targeted_move_ids()):

            cost = cost.with_company(cost.company_id)
            rounding = cost.currency_id.rounding
            total_qty = 0.0
            total_cost = 0.0
            total_weight = 0.0
            total_volume = 0.0
            total_line = 0.0
            all_val_line_values = cost.get_valuation_lines()

            print("all_val_line_values ===>> ", all_val_line_values)

            for val_line_values in all_val_line_values:
                for cost_line in cost.cost_lines:

                    if cost_line.bl_custom_id:
                        if cost_line.bl_custom_id.product_id.id == val_line_values['product_id']:
                            val_line_values.update({'cost_id': cost.id,
                                                    'cost_line_id': cost_line.id,
                                                    'bl_custom_id': cost_line.bl_custom_id.id,
                                                    'additional_landed_cost': cost_line.bl_custom_id.total_amount_landed_cost
                                                    })
                            self.env['stock.valuation.adjustment.lines'].create(val_line_values)

                    else:
                        val_line_values.update({'cost_id': cost.id, 'cost_line_id': cost_line.id})
                        self.env['stock.valuation.adjustment.lines'].create(val_line_values)
                total_qty += val_line_values.get('quantity', 0.0)
                total_weight += val_line_values.get('weight', 0.0)
                total_volume += val_line_values.get('volume', 0.0)

                former_cost = val_line_values.get('former_cost', 0.0)
                # round this because former_cost on the valuation lines is also rounded
                total_cost += cost.currency_id.round(former_cost)

                total_line += 1


            #Split custom duty if multiple expiry came on same container

            for line in cost.cost_lines:
                if line.bl_custom_id:
                    print("line XX ==>> ", line)
                    total_value = 0
                    for valuation in cost.valuation_adjustment_lines:


                        if valuation.cost_line_id.id == line.id:
                            total_value += valuation.former_cost

                    ratio = line.bl_custom_id.total_amount_landed_cost/total_value

                    for valuation in cost.valuation_adjustment_lines:
                        if valuation.cost_line_id.id == line.id:
                            valuation.additional_landed_cost = valuation.former_cost * ratio

            for line in cost.cost_lines:

                #No need to recalculate cost of custom duty
                if line.bl_custom_id:
                    continue
                value_split = 0.0
                for valuation in cost.valuation_adjustment_lines:

                    # No need to recalculate cost of custom duty
                    if valuation.bl_custom_id:
                        continue

                    value = 0.0
                    if valuation.cost_line_id and valuation.cost_line_id.id == line.id:
                        if line.split_method == 'by_quantity' and total_qty:
                            per_unit = (line.price_unit / total_qty)
                            value = valuation.quantity * per_unit
                        elif line.split_method == 'by_weight' and total_weight:
                            per_unit = (line.price_unit / total_weight)
                            value = valuation.weight * per_unit
                        elif line.split_method == 'by_volume' and total_volume:
                            per_unit = (line.price_unit / total_volume)
                            value = valuation.volume * per_unit
                        elif line.split_method == 'equal':
                            value = (line.price_unit / total_line)
                        elif line.split_method == 'by_current_cost_price' and total_cost:
                            per_unit = (line.price_unit / total_cost)
                            value = valuation.former_cost * per_unit
                        else:
                            value = (line.price_unit / total_line)

                        if rounding:
                            value = tools.float_round(value, precision_rounding=rounding, rounding_method='UP')
                            fnc = min if line.price_unit > 0 else max
                            value = fnc(value, line.price_unit - value_split)
                            value_split += value

                        if valuation.id not in towrite_dict:
                            towrite_dict[valuation.id] = value
                        else:
                            towrite_dict[valuation.id] += value
        for key, value in towrite_dict.items():
            AdjustementLines.browse(key).write({'additional_landed_cost': value})
        return True


class StockLandedCostLine(models.Model):
    _inherit = 'stock.landed.cost.lines'

    bl_custom_id = fields.Many2one('bl.entry.cost.customs', "Bl Customs Cost")


class AdjustmentLines(models.Model):
    _inherit = 'stock.valuation.adjustment.lines'

    bl_custom_id = fields.Many2one('bl.entry.cost.customs', "Bl Customs Cost")






