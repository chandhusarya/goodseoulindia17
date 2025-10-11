from odoo import models

class Picking(models.Model):
    _inherit = "stock.picking"

    def _action_done(self):
        context = dict(self.env.context, do_not_unreserve = True, do_not_propagate = True, mail_notrack = True, tracking_disable = True)
        for move in self.with_context(tracking_disable = True).move_ids:
            if move.product_id.cost_level == 'lot' and len(move.move_line_ids) > 1 and move.product_id.type == 'product':
                line1_initial_demand = move.product_uom_qty
                for move_line in move.move_line_ids[1:]:
                    if move_line.quantity:
                        new_move = move.with_context(context).copy(default={
                            'product_uom_qty': move_line.quantity,
                            'price_unit': move.price_unit,
                            'move_orig_ids': [(6, 0, move.move_orig_ids.ids)],
                            'move_dest_ids': [(6, 0, move.move_dest_ids.ids)]
                            })
                        move_line.with_context(context).write({
                          'move_id': new_move.id,
                          'quantity': move_line.quantity
                        })
                        new_move.with_context(context)._action_confirm(merge=False)
                        line1_initial_demand -=  new_move.product_uom_qty
                    else:
                        move_line.with_context(context).write({'move_id': None, 'picking_id': None, 'state': 'draft'})
                    move.with_context(context).write({'product_uom_qty': line1_initial_demand})
        return super(Picking, self)._action_done()