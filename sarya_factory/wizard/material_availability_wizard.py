from odoo import models, fields, api

class MaterialRequestAvailabilityWizard(models.TransientModel):
    _name = 'material.request.availability.wizard'
    _description = 'Material Request Availability Wizard'

    request_id = fields.Many2one('material.request', string='Material Request', readonly=True)
    is_transfered = fields.Boolean(
        string='Transfered',
        default=False, copy=False)
    is_lpo_created = fields.Boolean(
        string='LPO Created',
        default=False, copy=False)
    availability_lines = fields.One2many('material.request.availability.wizard.line', 'wizard_id', string='Availability Lines')

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        request_id = self.env.context.get('default_request_id')
        if request_id:
            request = self.env['material.request'].browse(request_id)
            lines = []
            for line in request.request_lines:
                location_id = request.location_id
                stock_quant = self.env['stock.quant'].search([
                    '|', ('location_id', '=', location_id.id), ('location_id.location_id', '=', location_id.id),
                    ('product_id', '=', line.product_id.id)
                ])
                qty_available = sum(stock_quant.mapped('quantity'))
                pkg_qty = qty_available/line.packaging_id.qty
                requested_qty = line.requested_qty
                if requested_qty < pkg_qty:
                    transfer_qty = requested_qty
                    po_qty = 0
                elif pkg_qty < requested_qty:
                    transfer_qty = pkg_qty
                    po_qty = requested_qty - transfer_qty
                lines.append((0, 0, {
                    'request_line_id': line.id,
                    'product_id': line.product_id.id,
                    'packaging_id': line.packaging_id.id,
                    'requested_qty': line.requested_qty,
                    'on_hand_qty': qty_available,
                    'available_qty': pkg_qty,
                    'transfer_qty': transfer_qty,
                    'po_qty': po_qty,
                }))
            res['availability_lines'] = lines
        return res

    def action_create_internal_transfer(self):
        operation_type = self.env['stock.picking.type'].search([('code', '=', 'internal')])
        location_id = self.request_id.location_id
        location_dest_id = self.request_id.location_dest_id
        move_lines = []
        for line in self.availability_lines:
            move_vals = line.prepare_picking_line_int_transfer(location_id, location_dest_id,
                                                               description=self.request_id.name)
            move_lines.append((0, 0, move_vals))
            # move = self.env['stock.move'].create(move_vals)
            line.request_line_id.transferred_qty = line.transfer_qty
            # print('Line', move)
        picking_vals = {
            'picking_type_id': operation_type[0].id,
            'user_id': False,
            'date': fields.Datetime.now(),
            'origin': self.request_id.name,
            'location_dest_id': location_dest_id and location_dest_id.id,
            'location_id': location_id and location_id.id,
            'company_id': self.env.company.id,
            'move_ids': move_lines,
        }
        print("picking_vals", picking_vals)
        picking = self.env['stock.picking'].create(picking_vals)
        print('Picking', picking)
        self.request_id.picking_ids = [(4, picking.id)]
        self.request_id.is_transfered = True
        return self


    def action_create_purchase_order(self):
        pur_obj = self.env['local.purchase']

        self.request_id.is_lpo_created = True

class MaterialRequestAvailabilityWizardLine(models.TransientModel):
    _name = 'material.request.availability.wizard.line'
    _description = 'Material Request Availability Wizard Line'

    wizard_id = fields.Many2one('material.request.availability.wizard', string='Wizard')
    request_line_id = fields.Many2one('material.request.line', string='Request Line')
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    packaging_id = fields.Many2one(comodel_name='product.packaging', string='Packaging',
        domain="[('purchase', '=', True), ('product_id', '=', product_id)]")
    requested_qty = fields.Float(string='Requested Quantity', readonly=True)
    available_qty = fields.Float(string='Available Quantity')
    transfer_qty = fields.Float(string='Transfer Quantity')
    po_qty = fields.Float(string='PO Quantity')
    on_hand_qty = fields.Float(string='On Hand(Units)', readonly=True)

    @api.onchange('transfer_qty')
    def onchange_transfer_qty(self):
        pkg_qty = self.product_id.qty_available / self.packaging_id.qty
        self.po_qty = pkg_qty - self.requested_qty


    def prepare_picking_line_int_transfer(self, location_id, location_dest_id, description=''):
        self.ensure_one()
        # Finding qty against each lot received for same product
        product_uom_qty = self.transfer_qty * self.packaging_id.qty
        product_uom = self.product_id.uom_id


        vals = {
            'product_id': self.product_id.id,
            'date': fields.Datetime.now(),
            'location_id': location_id and location_id.id,
            'location_dest_id': location_dest_id and location_dest_id.id,
            # 'picking_id': picking.id,
            'company_id': self.env.company.id,
            'origin': description,
            'name': self.product_id.name,
            # 'price_unit': price_unit,
            'quantity': product_uom_qty,
            'product_uom_qty': product_uom_qty,
            'product_uom': product_uom.id,
        }
        return vals



