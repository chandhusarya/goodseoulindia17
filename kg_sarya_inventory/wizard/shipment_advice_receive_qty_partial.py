from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ShipmentAdviceReceiveQtyPartial(models.TransientModel):
    _name = 'shipment.advice.receive.qty.partial'

    shipment_advice_id = fields.Many2one('shipment.advice', string='Shipment Advice')
    summary_lines = fields.One2many('shipment.advice.receive.qty.partial.line', 'partial_id')

    def check_qualifed_qty(self, qty_for_mainstock, qty_received_in_inspection):
        if qty_for_mainstock > (qty_received_in_inspection/2):
            raise UserError(_('Without completing inspection you cannot transfer more than 50% of stock'))


    def do_transfer(self):

        is_any_transfer_required = False
        for line in self.summary_lines:
            if line.qty_for_mainstock > 0.001:
                is_any_transfer_required = True


            if self.shipment_advice_id.is_on_inspection and not self.shipment_advice_id.is_full_override_allowed:
                total_qty_transfer = line.qty_received_in_inspection - line.balance_qty_in_inspection
                total_qty_transfer = total_qty_transfer + line.qty_for_mainstock
                self.check_qualifed_qty(total_qty_transfer, line.qty_received_in_inspection)

        if not is_any_transfer_required:
            return False

        self.shipment_advice_id.state = 'item_received'

        shipment_advice_id = self.shipment_advice_id

        location_dest_id = shipment_advice_id.main_stock_location.id
        location_id = shipment_advice_id.inspection_location.id

        picking_type_id = self.env['stock.picking.type'].search([('name', '=', 'Internal Transfers')], limit=1)
        if not picking_type_id:
            raise UserError(_("Internal Transfers operation type is not found in system"))

        # Create picking and move lines
        picking_vals = {
            'picking_type_id': picking_type_id.id,
            'user_id': False,
            'date': fields.Datetime.now(),
            'origin': shipment_advice_id.name,
            'location_dest_id': location_dest_id,
            'location_id': location_id,
            'company_id': shipment_advice_id.company_id.id,
            'origin': shipment_advice_id.name + " : " + 'Inspection Override'
        }

        picking = self.env['stock.picking'].create(picking_vals)
        for line in self.summary_lines:
            if line.qty_for_mainstock > 0.001:
                move_vals = line.prepare_picking_line_int_transfer(picking, picking_type_id,
                                                                location_id, location_dest_id,
                                                                description=shipment_advice_id.name + " : " + 'Inspection Override')
                self.env['stock.move.line'].create(move_vals)
        picking.button_validate()
        picking.shipment_id = shipment_advice_id.id



class ShipmentAdviceReceiveQtyPartialLines(models.TransientModel):
    _name = 'shipment.advice.receive.qty.partial.line'

    partial_id = fields.Many2one('shipment.advice.receive.qty.partial', string='Shipment Advice')
    summary_line_id = fields.Many2one('shipment.summary.line', string='Summary Line')

    product_id = fields.Many2one('product.product')
    lot_id = fields.Many2one('stock.lot', string='Lot - Expiry')
    expiry_date = fields.Date("Expiry Date")
    production_date = fields.Date("Production")
    qty_received_in_inspection = fields.Float("Qty Received")
    balance_qty_in_inspection = fields.Float("Balance Qty")
    qty_for_mainstock = fields.Float(string="Qty to Transfer")

    def prepare_picking_line_int_transfer(self, picking, picking_type_id,
                                          location_id, location_dest_id, description=''):
        self.ensure_one()
        vals = []

        # Finding qty against each lot received for same product

        total_qty_received = self.qty_for_mainstock
        self.summary_line_id.qty_moved_to_main_stock = self.summary_line_id.qty_moved_to_main_stock + total_qty_received

        packaging_uom = self.summary_line_id.summary_id.product_packaging_id.product_uom_id
        qty_per_packaging = self.summary_line_id.summary_id.product_packaging_id.qty

        total_qty_received = total_qty_received * qty_per_packaging

        product_uom_qty, product_uom = packaging_uom._adjust_uom_quantities( total_qty_received, self.product_id.uom_id)

        vals.append({
            'product_id': self.product_id.id,
            'date': fields.Datetime.now(),
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'picking_id': picking.id,
            'lot_id': self.lot_id.id,
            'company_id': self.summary_line_id.summary_id.purchase_line_id.order_id.company_id.id,
            'origin': description,
            'quantity': product_uom_qty,
            'product_uom_id': product_uom.id,
            'product_packaging_id': self.summary_line_id.summary_id.product_packaging_id.id,
        })
        return vals