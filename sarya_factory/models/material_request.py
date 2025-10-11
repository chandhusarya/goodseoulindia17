from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class MaterialRequest(models.Model):
    _name = 'material.request'
    _description = 'Material Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(default='/')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company,
                                 readonly=True)
    requested_by = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user)
    date = fields.Datetime(string='Request Date', default=fields.Datetime.now)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('manager_approval', 'Manager Approval'),
        ('approved', 'Approved'),
        ('cancel', 'Cancelled'),
    ], default='draft', string='State', tracking=True)
    request_lines = fields.One2many('material.request.line', 'request_id', string='Request Lines')
    # picking_type_id = fields.Many2one(
    #     comodel_name='stock.picking.type',
    #     string='Picking Type',
    #     required=True)
    # location_id = fields.Many2one(
    #     comodel_name='stock.location',
    #     string='Source Location',
    #     required=True)
    # location_dest_id = fields.Many2one(
    #     comodel_name='stock.location',
    #     string='Destination Location',
    #     required=True)
    picking_ids = fields.Many2many(
        comodel_name='stock.picking',
        string='Pickings', copy=False)
    picking_count = fields.Integer(string="Picking Count", compute="_compute_picking_count")
    lpo_ids = fields.Many2many(
        comodel_name='local.purchase',
        string='LPOs', copy=False)
    lpo_count = fields.Integer(string="LPO Count", compute="_compute_lpo_count")
    is_transfered = fields.Boolean(
        string='Transfered',
        default=False, copy=False)
    is_lpo_created = fields.Boolean(
        string='LPO Created',
        default=False, copy=False)

    @api.depends('picking_ids')
    def _compute_picking_count(self):
        for record in self:
            record.picking_count = len(record.picking_ids)

    def action_view_pickings(self):
        return {
            'name': 'Related Pickings',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'domain': [('origin', '=', self.name)],  # Filter by request name as origin
            'context': {'create': False}
        }

    @api.depends('lpo_ids')
    def _compute_lpo_count(self):
        for record in self:
            record.lpo_count = len(record.lpo_ids)

    def action_view_lpos(self):
        action = self.env.ref("sarya_factory.local_purchase_factory_act_window").sudo().read()[0]
        action['domain'] = [('material_request_id', '=', self.id)]
        return action


    def action_request(self):
        users = self.env.ref('sarya_factory.can_approve_mr').users
        email_to = ""
        for usr in users:
            if usr.partner_id.email:
                if not email_to:
                    email_to = usr.partner_id.email
                else:
                    email_to = email_to + ', ' + usr.partner_id.email

        main_content = {
            'subject': _('Material Request: No. %s approval request' % self.name),
            'author_id': self.env.user.partner_id.id,
            'body_html': 'Hi,<br><br>Material request %s is waiting for your approval.' % self.name,
            'email_to': email_to,
        }
        self.env['mail.mail'].sudo().create(main_content).send()
        self.state = 'manager_approval'

    def action_approve(self):
        self.state = 'approved'
    def action_reset(self):
        self.state = 'draft'

    def action_cancel(self):
        self.state = 'cancel'

    def action_check_availability(self):
        return {
            'name': 'Check Availability',
            'type': 'ir.actions.act_window',
            'res_model': 'material.request.availability.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_id': self.id,
                'default_is_transfered':self.is_transfered,
                'default_is_lpo_created':self.is_lpo_created
            },
        }

    def action_transfer(self):
        """ Create Internal Transfers grouped by (location_id, location_dest_id) """
        self.ensure_one()
        Picking = self.env['stock.picking']
        Move = self.env['stock.move']
        MoveLine = self.env['stock.move.line']
        pickings = []

        transfers = {}  # Dictionary to store picking per (source, destination) pair

        for line in self.request_lines:
            if (not line.location_id or not line.location_dest_id) and not line.local_purchase:
                raise UserError("Location missing for item %s"%(line.product_id.name))
            key = (line.location_id.id, line.location_dest_id.id)

            if len(line.detail_ids) == 0:
                continue

            if key not in transfers:
                # Create a new picking for this location pair
                picking = Picking.create({
                    'picking_type_id': self.env.ref('stock.picking_type_internal').id,  # Internal Transfer Type
                    'location_id': line.location_id.id,
                    'location_dest_id': line.location_dest_id.id,
                    'origin': self.name,
                })
                pickings.append((4,picking.id))
                transfers[key] = picking  # Store picking reference for this location pair

            # Create stock move under the respective picking
            if len(line.detail_ids) == 0:
                raise UserError("No batch selected for item %s"%(line.product_id.name))
            move = Move.create({
                'picking_id': transfers[key].id,
                'name': f"{line.product_id.name} Transfer",
                'product_id': line.product_id.id,
                'product_uom_qty': line.transferred_qty,  # Ensure this matches stock.move.line sum
                'product_uom': line.product_id.uom_po_id.id,
                'location_id': line.location_id.id,
                'location_dest_id': line.location_dest_id.id,
                'state': 'draft',  # Ensures proper reservation
            })
            for detail in line.detail_ids:
                MoveLine.create({
                    'move_id': move.id,
                    'picking_id': transfers[key].id,
                    'product_id': detail.product_id.id,
                    'quantity': detail.quantity,
                    'product_uom_id': detail.product_uom_id.id,
                    'location_id': line.location_id.id,
                    'location_dest_id': line.location_dest_id.id,
                    'quant_id': detail.quant_id.id,
                    'lot_id': detail.quant_id.lot_id and detail.quant_id.lot_id.id,
                })
        self.is_transfered = True
        self.picking_ids = pickings

    def action_create_po(self):
        self.ensure_one()
        PO = self.env['local.purchase']
        POLine = self.env['local.purchase.line']
        lpos = []

        picking_types = {}  # Dictionary to store picking per (source, destination) pair
        for line in self.request_lines:
            if line.ordered_qty > 0:
                if not line.supplier_id:
                    raise UserError("Supplier missing for item %s"%(line.product_id.name))
                if not line.picking_type_id:
                    raise UserError("Picking Type missing for item %s"%(line.product_id.name))
                key = (line.picking_type_id.id, line.supplier_id.id)
                picking_type = line.picking_type_id
                if key not in picking_types:
                    order = PO.create({
                        'vendor_id': line.supplier_id.id,
                        'material_request_id': self.id,
                        'purchase_type': 'normal',
                        'picking_type_id': line.picking_type_id and line.picking_type_id.id,
                    })
                    picking_types[key] = order
                    lpos.append((4,order.id))
                # po_qty_primary = line.requested_qty_primary - line.transferred_qty
                # po_qty = (po_qty_primary/line.packaging_id.qty)
                POLine.create({
                    'local_purchase_id': picking_types[key].id,
                    'product_id': line.product_id.id,
                    'name': line.product_id.name,
                    'packaging_id': line.packaging_id.id,
                    'qty': line.ordered_qty,
                    'unit_price': line.product_id.uom_po_id and line.product_id.uom_po_id.id,
                    'tax_ids': line.product_id.supplier_taxes_id,
                })
        self.is_lpo_created = True
        self.lpo_ids = lpos


    @api.model
    def create(self, values):
        if self.env.company.company_type == 'retail':
            values['name'] = self.env['ir.sequence'].next_by_code('material.request.ret')
        if self.env.company.company_type == 'distribution':
            values['name'] = self.env['ir.sequence'].next_by_code('material.request.dist')
        return super(MaterialRequest, self).create(values)

    def unlink(self):
        if self.state != 'draft':
            raise ValidationError('Deleting the record only possible at DRAFT status.')
        return super(MaterialRequest, self).unlink()

    @api.onchange('picking_type_id')
    def onchange_picking(self):
        if self.picking_type_id:
            self.location_dest_id = self.picking_type_id.default_location_src_id and self.picking_type_id.default_location_src_id.id

class MaterialRequestLine(models.Model):
    _name = 'material.request.line'
    _description = 'Material Request Line'

    request_id = fields.Many2one('material.request', string='Material Request')
    is_transfered = fields.Boolean(related='request_id.is_transfered')
    is_lpo_created = fields.Boolean(related='request_id.is_lpo_created')
    product_id = fields.Many2one('product.product', string='Product')#, domain=[('section.name', '=', 'Good Seoul Factory')])
    packaging_id = fields.Many2one(comodel_name='product.packaging', string='Packaging',
        domain="[('product_id', '=', product_id)]")
    primary_packaging_id = fields.Many2one(comodel_name='product.packaging', string='Primary Packaging',
        domain="[('primary_unit', '=', True), ('product_id', '=', product_id)]")
    requested_qty = fields.Float(string='Requested Qty')
    requested_qty_primary = fields.Float(string='Requested Qty Primary')
    # available_qty = fields.Float(string='Available Qty', compute='_compute_on_hand_qty')
    transferred_qty = fields.Float(string='Done Qty', compute='_compute_transferred_qty')
    transferred_pkg_qty = fields.Float(string='Done Qty', compute='_compute_transferred_qty')
    balance_pkg_qty = fields.Float(string='Balance To Order', compute='_compute_transferred_qty')
    ordered_qty = fields.Float(string='LPO Qty')
    supplier_id = fields.Many2one('res.partner', string='Supplier', domain=[('supplier_rank', '>', 0)])
    on_hand_qty = fields.Float(string='On Hand Qty', compute='_compute_on_hand_qty')
    detail_ids = fields.One2many('material.request.line.details', 'request_line_id', string='Request Lines')
    location_id = fields.Many2one('stock.location', string='From Location', domain=[('usage', '=', 'internal')])
    location_dest_id = fields.Many2one('stock.location', string='To Location', domain=[('usage', '=', 'internal')])
    picking_type_id = fields.Many2one(comodel_name='stock.picking.type', string='Picking Type', domain=[('code', '=', 'incoming')])
    local_purchase = fields.Boolean(string="Local Purchase", copy=False, default=False)

    # @api.depends('product_id', 'packaging_id')
    # def _compute_on_hand_qty(self):
    #     for line in self:
    #         if not line.request_id.location_id:
    #             raise ValidationError("Location missing under details tab.")
    #         if line.product_id and line.packaging_id:
    #             location_id = line.request_id.location_id
    #             stock_quant = self.env['stock.quant'].search([
    #                 ('location_id', '=', location_id.id),
    #                 ('product_id', '=', line.product_id.id)
    #             ])
    #             total_qty = sum(stock_quant.mapped('quantity'))
    #             line.on_hand_qty = total_qty
    #             line.available_qty = (total_qty)/(line.packaging_id.qty)
    #         else:
    #             line.on_hand_qty = 0
    #             line.available_qty = 0

    @api.depends('detail_ids')
    def _compute_transferred_qty(self):
        for line in self:
            total_quantity = 0
            for detail in line.detail_ids:
                total_quantity += detail.quantity
            line.transferred_qty = total_quantity
            line.transferred_pkg_qty = total_quantity/line.packaging_id.qty
            line.balance_pkg_qty = line.requested_qty - line.transferred_pkg_qty

    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            packaging = self.env['product.packaging'].search([
                ('product_id', '=', self.product_id.id), ('primary_unit', '=', True)], limit=1)
            self.packaging_id = False
            self.primary_packaging_id = packaging and packaging.id

    @api.onchange('requested_qty')
    def onchange_requested_qty(self):
        if self.requested_qty > 0:
            self.requested_qty_primary = self.requested_qty * self.packaging_id.qty

    def action_open_line_details(self):
        """ Open the form view of Material Request Line with its details """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Material Request Line',
            'res_model': 'material.request.line',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',  # Opens in a popup
        }

class MaterialRequestLineDetails(models.Model):
    _name = 'material.request.line.details'
    _description = 'Material Request Line Details'

    request_id = fields.Many2one('material.request', string='Material Request')
    request_line_id = fields.Many2one('material.request.line', string='Material Request Line')
    product_id = fields.Many2one('product.product', string='Product')
    location_id = fields.Many2one('stock.location', string='From Location', domain=[('usage', '=', 'internal')])
    quant_id = fields.Many2one('stock.quant', 'Pick From')
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure')
    quantity = fields.Float(string='Quantity')

    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_po_id
        else:
            self.product_uom_id = False

    @api.onchange('quant_id')
    def onchange_quant_id(self):
        if self.quant_id and self.quant_id.available_quantity > 0:
            balance = (self.request_line_id.requested_qty_primary - self.request_line_id.transferred_qty)
            available_qty = self.quant_id.available_quantity
            if available_qty < balance:
                self.quantity = available_qty
            elif balance < available_qty:
                self.quantity = balance
            else:
                self.quantity = 0

    @api.constrains('request_id', 'product_id', 'quant_id')
    def validate_quant_duplicate(self):
        for rec in self:
            count = self.env['material.request.line.details'].search_count([
                ('request_line_id', '=', rec.request_line_id.id), ('product_id', '=', rec.product_id.id),
                ('quant_id', '=', rec.quant_id.id)
            ])
            if count > 1:
                raise ValidationError("Batch/Lot already chosen.")


