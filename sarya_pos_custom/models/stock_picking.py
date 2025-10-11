from odoo import fields, models, api



# class StockMove(models.Model):
#     _inherit = 'stock.move'
#
#     def _add_mls_related_to_order(self, related_order_lines, are_qties_done=True):
#         lines_data = self._prepare_lines_data_dict(related_order_lines)
#         qty_fname = 'quantity' if are_qties_done else 'product_uom_qty'
#         # Moves with product_id not in related_order_lines. This can happend e.g. when product_id has a phantom-type bom.
#         moves_to_assign = self.filtered(lambda m: m.product_id.id not in lines_data or m.product_id.tracking == 'none'
#                                                   or (not m.picking_type_id.use_existing_lots and not m.picking_type_id.use_create_lots))
#         for move in moves_to_assign:
#             move.quantity = move.product_uom_qty
#         moves_remaining = self - moves_to_assign
#         existing_lots = moves_remaining._create_production_lots_for_pos_order(related_order_lines)
#         print('********************ACTUAL**********************')
#         print('********************ACTUAL**********************')
#         print('_add_mls_related_to_order() - existing_lots - ', existing_lots)
#         print('_add_mls_related_to_order() - lines_data - ', lines_data)
#         print('_add_mls_related_to_order() - moves_remaining - ', moves_remaining)
#         print('********************ACTUAL**********************')
#         print('********************ACTUAL**********************')
#         move_lines_to_create = []
#         mls_qties = []
#         if are_qties_done:
#             for move in moves_remaining:
#                 move.move_line_ids.quantity = 0
#                 for line in lines_data[move.product_id.id]['order_lines']:
#                     sum_of_lots = 0
#                     for lot in line.pack_lot_ids.filtered(lambda l: l.lot_name):
#                         qty = 1 if line.product_id.tracking == 'serial' else abs(line.qty)
#                         ml_vals = dict(move._prepare_move_line_vals(qty))
#                         if existing_lots:
#                             existing_lot = existing_lots.filtered_domain([('product_id', '=', line.product_id.id), ('name', '=', lot.lot_name)])
#                             quant = self.env['stock.quant']
#                             if existing_lot:
#                                 quant = self.env['stock.quant'].search(
#                                     [('lot_id', '=', existing_lot.id), ('quantity', '>', '0.0'), ('location_id', 'child_of', move.location_id.id)],
#                                     order='id desc',
#                                     limit=1
#                                 )
#                             ml_vals.update({
#                                 'quant_id': quant.id,
#                             })
#                         else:
#                             ml_vals.update({'lot_name': lot.lot_name})
#                         move_lines_to_create.append(ml_vals)
#                         mls_qties.append(qty)
#                         sum_of_lots += qty
#                     if abs(line.qty) != sum_of_lots:
#                         difference_qty = abs(line.qty) - sum_of_lots
#                         ml_vals = move._prepare_move_line_vals()
#                         if line.product_id.tracking == 'serial':
#                             move_lines_to_create.extend([ml_vals for i in range(int(difference_qty))])
#                             mls_qties.extend([1]*int(difference_qty))
#                         else:
#                             move_lines_to_create.append(ml_vals)
#                             mls_qties.append(difference_qty)
#             move_lines = self.env['stock.move.line'].create(move_lines_to_create)
#             print('_add_mls_related_to_order() - move_lines_to_create', move_lines_to_create)
#             print('_add_mls_related_to_order() - move_lines', move_lines)
#             for move_line, qty in zip(move_lines, mls_qties):
#                 move_line.write({qty_fname: qty})
#         else:
#             for move in moves_remaining:
#                 for line in lines_data[move.product_id.id]['order_lines']:
#                     for lot in line.pack_lot_ids.filtered(lambda l: l.lot_name):
#                         if line.product_id.tracking == 'serial':
#                             qty = 1
#                         else:
#                             qty = abs(line.qty)
#                         if existing_lots:
#                             existing_lot = existing_lots.filtered_domain([('product_id', '=', line.product_id.id), ('name', '=', lot.lot_name)])
#                             if existing_lot:
#                                 move._update_reserved_quantity(qty, move.location_id, lot_id=existing_lot)
#                                 continue


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    outlet_transfer_id = fields.Many2one(
        'outlet.transfer',
        string='Outlet Transfer'
    )