from odoo import models, fields, _, api
from odoo.exceptions import UserError


class PricelistWizard(models.Model):
    _name = 'shipment.inspection'
    _description = 'Shipment Inspected Qty'

    name = fields.Char('Name',default='Inspection')
    shipment_id = fields.Many2one('shipment.advice', readonly=True)
    shipment_lines = fields.One2many(comodel_name='shipment.inspection.line', inverse_name='inspection_id',
                                     string='Shipment Products')
    shipment_summerlines = fields.One2many(comodel_name='shipment.inspection.line', inverse_name='inspection_id',
                                     string='Shipment Products', tracking=True)
    # @api.onchange('shipment_id')
    # def onchange_shipment(self):
    #     for data in self:
    #         order_line = []
    #         for line in data.shipment_id.shipment_lines:
    #             print(line.product_id.name)
    #             product_line = (0,0,{'product_id': line.product_id.id,
    #                                    'state': line.state,
    #                                    'purchase_id': line.purchase_id.id,
    #                                    'purchase_line_id': line.purchase_line_id.id,
    #                                    'company_id': line.company_id.id,
    #                                    'product_packaging_id': line.product_packaging_id.id,
    #                                    'open_packaging_qty': line.open_packaging_qty,
    #                                    'shipped_packaging_qty': line.shipped_packaging_qty,
    #                                    'received_qty': line.received_qty,
    #                                    'received_packaging_qty': line.received_packaging_qty,
    #                                    'inspected_packaging_qty': line.inspected_packaging_qty,
    #                                    'is_inspected': line.is_inspected})
    #             print(product_line)
    #             order_line.append(product_line)
    #             print(order_line)
    #         data.write({'shipment_lines':order_line})


    def update_inspected_qty(self):
        lines_list = []
        qty_avl = 0
        for line in self.shipment_lines:
            print('e')
            product_line = (0,0,{'product_id': line.product_id.id,
                                'state': line.state,
                                'purchase_id': line.purchase_id.id,
                                'purchase_line_id': line.purchase_line_id.id,
                                'company_id': line.company_id.id,
                                'product_packaging_id': line.product_packaging_id.id,
                                'open_packaging_qty': line.open_packaging_qty,
                                'shipped_packaging_qty': line.shipped_packaging_qty,
                                'received_qty': line.received_qty,
                                'received_packaging_qty': line.received_packaging_qty,
                                'inspected_packaging_qty': line.inspected_packaging_qty,
                                'is_inspected': line.is_inspected})
            lines_list.append(product_line)
            print(lines_list)
            if any(line.inspected_packaging_qty <= 0.0 for line in self.shipment_lines):
                raise UserError(_("Inspected qty should be greater than zero."))
            if any(line.inspected_packaging_qty > line.open_packaging_qty for line in self.shipment_lines):
                raise UserError(_("Inspected qty should be Less than Open Qty."))
        self.shipment_id.shipment_lines = False
        self.shipment_id.write({'shipment_lines': lines_list,
                                'is_inspected': True})

        return {
                'name': _('Inspection Details'),
                'res_model': 'shipment.advice',
                'type': 'ir.actions.act_window',
                'view_id': False,
                'res_id': self.shipment_id.id,
                'view_mode': 'form',
                'view_type': 'form',
            }

class PricelistWizardline(models.Model):
    _name = 'shipment.inspection.line'
    _description = 'Shipment Inspected Line'

    inspection_id = fields.Many2one(
        'shipment.inspection', 'Shipment', ondelete='cascade', required=True)
    shipment_id = fields.Many2one('shipment.advice',related='inspection_id.shipment_id')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    purchase_id = fields.Many2one('purchase.order', 'Purchase', ondelete='cascade', required=True, copy=False,
                                  domain="[('state', 'in', ('purchase', 'done')), ('stock_type', '=', 'inventory')]")
    purchase_line_id = fields.Many2one(
        'purchase.order.line', 'Product Description', required=True,
        domain="[('order_id', '=', purchase_id), ('order_id', '=', purchase_id), ('product_id', '=', product_id)]")
    company_id = fields.Many2one(related='shipment_id.company_id')
    product_packaging_id = fields.Many2one(related='purchase_line_id.product_packaging_id')
    open_packaging_qty = fields.Float(string='Open Qty', readonly=1)
    shipped_packaging_qty = fields.Float(string='Shipped Qty', digits='Product Unit of Measure')
    received_qty = fields.Float(string='Rec. Qty(Unit)', digits='Product Unit of Measure',
                                related='purchase_line_id.qty_received')
    received_packaging_qty = fields.Float(string='Received Qty', digits='Product Unit of Measure')
    inspected_packaging_qty = fields.Float(string='Inspected Qty', digits='Product Unit of Measure')
    is_inspected = fields.Boolean(string='Inspected', default=False)
    state = fields.Selection(string='Shipment Status', related='shipment_id.state')