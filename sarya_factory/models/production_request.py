from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class ProductionRequest(models.Model):
    _name = 'production.request'
    _description = 'Production Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(default='/')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company,
                                 readonly=True)
    requested_by = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user)
    date = fields.Datetime(string='Request Date', default=fields.Datetime.now)

    stock_required_date = fields.Date(string='Stock Required On', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('manager_approval', 'Waiting Approval'),
        ('approved', 'Approved'),
        ('completed', 'Completed'),
        ('cancel', 'Cancelled'),
    ], default='draft', string='State', tracking=True)
    request_lines = fields.One2many('production.request.line', 'request_id', string='Request Lines')
    picking_ids = fields.Many2many(
        comodel_name='stock.picking',
        string='Pickings', copy=False)
    picking_count = fields.Integer(string="Picking Count", compute="_compute_picking_count")

    is_transfered = fields.Boolean(
        string='Transfered',
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



    def action_request(self):

        for line in self.request_lines:
            if line.requested_qty <=0:
                raise UserError("Requested quantity must be greater than zero for product %s." % (line.product_id.name))

        users = self.env.ref('sarya_factory.can_approve_production_req').users
        email_to = ""
        for usr in users:
            if usr.partner_id.email:
                if not email_to:
                    email_to = usr.partner_id.email
                else:
                    email_to = email_to + ', ' + usr.partner_id.email

        main_content = {
            'subject': _('Production Material Request: No. %s approval request' % self.name),
            'author_id': self.env.user.partner_id.id,
            'body_html': 'Hi,<br><br>Production Material request %s is waiting for your approval.' % self.name,
            'email_to': email_to,
        }
        self.env['mail.mail'].sudo().create(main_content).send()
        self.state = 'manager_approval'

    def action_approve(self):
        self.state = 'approved'
        users = self.env.ref('sarya_factory.can_transfer_production_req').users
        email_to = ""
        for usr in users:
            if usr.partner_id.email:
                if not email_to:
                    email_to = usr.partner_id.email
                else:
                    email_to = email_to + ', ' + usr.partner_id.email

        main_content = {
            'subject': _('Production Material Request: No. %s is Approved' % self.name),
            'author_id': self.env.user.partner_id.id,
            'body_html': 'Hi,<br><br>Production Material request %s is approved. Please transfer the materials' % self.name,
            'email_to': email_to,
        }
        self.env['mail.mail'].sudo().create(main_content).send()



    def action_reset(self):
        self.state = 'draft'

    def action_cancel(self):
        self.state = 'cancel'


    def action_transfer(self):
        """ Create Internal Transfers grouped by (location_id, location_dest_id) """
        self.ensure_one()
        Picking = self.env['stock.picking']
        Move = self.env['stock.move']
        MoveLine = self.env['stock.move.line']
        pickings = []
        picking_ids = []

        transfers = {}  # Dictionary to store picking per (source, destination) pair

        for line in self.request_lines:

            for detail in line.detail_ids:

                if detail.quantity <= 0:
                    raise UserError("Quantity must be greater than zero for item %s"%(detail.product_id.name))
                if not detail.quant_id:
                    raise UserError("No batch selected for item %s"%(detail.product_id.name))

                from_location = detail.quant_id.location_id.id
                if line.fryer_location_dest_id:
                    to_location = line.fryer_location_dest_id.id
                else:
                    to_location = line.production_location_id.id

                key = (from_location, to_location)

                if detail.quant_id.available_quantity < detail.quantity:
                    raise UserError("Insufficient stock for item %s in batch %s. Available: %s, Requested: %s" % (
                        detail.product_id.name, detail.quant_id.lot_id.name, detail.quant_id.available_quantity, detail.quantity))


                if key not in transfers:
                    # Create a new picking for this location pair
                    picking = Picking.create({
                        'picking_type_id': self.env.ref('stock.picking_type_internal').id,  # Internal Transfer Type
                        'location_id': from_location,
                        'location_dest_id': to_location,
                        'origin': self.name,
                    })
                    pickings.append((4,picking.id))
                    picking_ids.append(picking)
                    transfers[key] = picking  # Store picking reference for this location pair

                # Create stock move under the respective picking
                if len(line.detail_ids) == 0:
                    raise UserError("No batch selected for item %s"%(line.product_id.name))
                move = Move.create({
                    'picking_id': transfers[key].id,
                    'name': f"{line.product_id.name} Transfer",
                    'product_id': line.product_id.id,
                    'product_uom_qty': detail.quantity,  # Ensure this matches stock.move.line sum
                    'product_uom': line.product_id.uom_po_id.id,
                    'location_id': from_location,
                    'location_dest_id': to_location,
                    'state': 'draft',  # Ensures proper reservation
                })

                MoveLine.create({
                    'move_id': move.id,
                    'picking_id': transfers[key].id,
                    'product_id': detail.product_id.id,
                    'quantity': detail.quantity,
                    'product_uom_id': detail.product_uom_id.id,
                    'location_id': from_location,
                    'location_dest_id': to_location,
                    'quant_id': detail.quant_id.id,
                    'lot_id': detail.quant_id.lot_id and detail.quant_id.lot_id.id,
                })
        self.is_transfered = True
        for picking in picking_ids:
            picking.action_confirm()
            picking.button_validate()
        self.picking_ids = pickings


    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].next_by_code('production.request.ret')
        return super(ProductionRequest, self).create(values)

    def unlink(self):
        if self.state != 'draft':
            raise ValidationError('Deleting the record only possible at DRAFT status.')
        return super(ProductionRequest, self).unlink()

    @api.onchange('picking_type_id')
    def onchange_picking(self):
        if self.picking_type_id:
            self.location_dest_id = self.picking_type_id.default_location_src_id and self.picking_type_id.default_location_src_id.id

class ProductionRequestLine(models.Model):
    _name = 'production.request.line'
    _description = 'Production Request Line'

    request_id = fields.Many2one('production.request', string='Material Request')
    is_transfered = fields.Boolean(related='request_id.is_transfered')
    product_id = fields.Many2one('product.product', string='Product')#, domain=[('section.name', '=', 'Good Seoul Factory')])
    packaging_id = fields.Many2one(comodel_name='product.packaging', string='Req Packaging',
        domain="[('product_id', '=', product_id)]")
    primary_packaging_id = fields.Many2one(comodel_name='product.packaging', string='Primary Packaging',
        domain="[('primary_unit', '=', True), ('product_id', '=', product_id)]")
    requested_qty = fields.Float(string='Req Qty')
    requested_qty_primary = fields.Float(string='Req Qty Primary')


    transferred_qty = fields.Float(string='Approved Qty', compute='_compute_transferred_qty')
    transferred_pkg_qty = fields.Float(string='Approved PKG Qty', compute='_compute_transferred_qty')
    on_hand_qty = fields.Float(string='Qty in Prd')
    on_hand_qty_storage = fields.Float(string='Qty in storage')


    detail_ids = fields.One2many('production.request.line.details', 'request_line_id', string='Request Lines')


    storage_location_id = fields.Many2one('stock.location', string='Storage Location', domain=[('usage', '=', 'internal')])
    production_location_id = fields.Many2one('stock.location', string='Production Location', domain=[('usage', '=', 'internal')])
    fryer_location_dest_id = fields.Many2one('stock.location', string='Fryer Location', domain=[('usage', '=', 'internal')])

    master_production_location_id = fields.Many2one('stock.location', string='Master Production Location', domain=[('usage', '=', 'view')])

    fryer_stock = fields.Boolean(string='For Fryer')

    picking_type_id = fields.Many2one(comodel_name='stock.picking.type', string='Picking Type', domain=[('code', '=', 'incoming')])

    @api.model
    def default_get(self, fields):
        res = super(ProductionRequestLine, self).default_get(fields)

        storage_location_id = self.env['stock.location'].search([('is_factory_storage_location', '=', True), ('usage', '=', 'view')], limit=1)
        if storage_location_id:
            res.update({'storage_location_id': storage_location_id.id})

        master_production_location_id = self.env['stock.location'].search([('is_factory_production_location', '=', True), ('usage', '=', 'internal')], limit=1)
        if master_production_location_id:
            res.update({'master_production_location_id': master_production_location_id.id})

        production_location_id = self.env['stock.location'].search([('is_factory_production_location', '=', True), ('usage', '=', 'internal')], limit=1)
        if production_location_id:
            res.update({'production_location_id': production_location_id.id})

        is_factory_fryer_location = self.env['stock.location'].search([('is_factory_fryer_location', '=', True)], limit=1)
        if is_factory_fryer_location and False:
            res.update({'fryer_location_dest_id': is_factory_fryer_location.id})

        return res


    @api.depends('detail_ids')
    def _compute_transferred_qty(self):
        for line in self:
            total_quantity = 0
            for detail in line.detail_ids:
                total_quantity += detail.quantity
            line.transferred_qty = total_quantity
            line.transferred_pkg_qty = total_quantity/line.packaging_id.qty


    @api.onchange('product_id')
    def onchange_product(self):
        primary_packaging_id = False
        on_hand_qty = 0
        on_hand_qty_storage = 0
        if self.product_id:
            packaging = self.env['product.packaging'].search([
                ('product_id', '=', self.product_id.id), ('primary_unit', '=', True)], limit=1)
            primary_packaging_id = packaging and packaging.id

            quants = self.env['stock.quant'].search([('location_id', 'child_of', self.master_production_location_id.id),
                                                    ('product_id', '=', self.product_id.id)
                                                    ])
            for q in quants:
                on_hand_qty += q.quantity

            storage_quants = self.env['stock.quant'].search(['|', ('location_id', '=', self.storage_location_id.id),
                                                     ('location_id', 'child_of', self.storage_location_id.id),
                                                     ('product_id', '=', self.product_id.id)
                                                     ])
            for q in storage_quants:
                on_hand_qty_storage += q.quantity

        self.packaging_id = primary_packaging_id
        self.primary_packaging_id = primary_packaging_id
        self.on_hand_qty = on_hand_qty
        self.on_hand_qty_storage = on_hand_qty_storage


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
            'res_model': 'production.request.line',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',  # Opens in a popup
        }

class ProductionRequestLineDetails(models.Model):
    _name = 'production.request.line.details'
    _description = 'production Request Line Details'

    request_id = fields.Many2one('production.request', string='Material Request')
    request_line_id = fields.Many2one('production.request.line', string='Material Request Line')
    product_id = fields.Many2one('product.product', string='Product')
    storage_location_id = fields.Many2one('stock.location', string='Storage Location', domain=[('usage', '=', 'internal')])
    quant_id = fields.Many2one('stock.quant', 'Lot/Expiry')
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure')
    total_stock = fields.Float(string='Total Stock')
    available_stock = fields.Float(string='Available Stock')
    quantity = fields.Float(string='Quantity')

    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_po_id
        else:
            self.product_uom_id = False

    @api.onchange('quant_id')
    def onchange_quant_id(self):
        available_stock = 0
        total_stock = 0
        quantity = 0
        if self.quant_id and self.quant_id.available_quantity > 0:
            balance = (self.request_line_id.requested_qty_primary - self.request_line_id.transferred_qty)
            available_qty = self.quant_id.available_quantity
            available_stock = self.quant_id.available_quantity

            total_stock = self.quant_id.quantity

            if available_qty < balance:
                quantity = available_qty
            elif balance < available_qty:
                quantity = balance
            else:
                quantity = 0

        self.total_stock = total_stock
        self.available_stock = available_stock
        self.quantity = quantity

    @api.constrains('request_id', 'product_id', 'quant_id')
    def validate_quant_duplicate(self):
        for rec in self:
            count = self.env['production.request.line.details'].search_count([
                ('request_line_id', '=', rec.request_line_id.id), ('product_id', '=', rec.product_id.id),
                ('quant_id', '=', rec.quant_id.id)
            ])
            if count > 1:
                raise ValidationError("Batch/Lot already chosen.")


