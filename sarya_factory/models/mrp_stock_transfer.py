from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class MrpStockTransfers(models.Model):
    _name = 'mrp.stock.transfer'
    _description = 'Stock Transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(default='/')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company, readonly=True)
    requested_by = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user)
    date = fields.Datetime(string='Request Date', default=fields.Datetime.now)

    state = fields.Selection([('draft', 'Draft'),
                              ('item_loaded', 'Items Loaded'),
        ('completed', 'Completed'),
        ('cancel', 'Cancelled')], default='draft', string='State', tracking=True)

    type = fields.Selection([('grn', 'GRN'),
                              ('finished', 'Finished/Intermediate Product'),
                              ('scraping', 'Scrapping')], default='grn', string='Type', tracking=True)

    from_location_id = fields.Many2one('stock.location', string='From Location')
    to_location_id = fields.Many2one('stock.location', string='To Location')


    from_location_id_grn = fields.Many2one('stock.location', string='From Location GRN', tracking=True)
    to_location_id_grn = fields.Many2one('stock.location', string='To Location GRN', tracking=True)

    from_location_id_finished = fields.Many2one('stock.location', string='From Location Finished', tracking=True)
    to_location_id_finished = fields.Many2one('stock.location', string='To Location Finished', tracking=True)

    from_location_id_scraping = fields.Many2one('stock.location', string='From Location Scraping', tracking=True)
    to_location_id_scraping = fields.Many2one('stock.location', string='To Location Scraping', tracking=True)


    transfer_lines = fields.One2many('mrp.stock.transfer.line', 'transfer_id', string='Transfer Lines')

    picking_count = fields.Integer(string="Picking Count", compute="_compute_picking_count")
    picking_ids = fields.Many2many(comodel_name='stock.picking', string='Pickings', copy=False)

    is_transfered = fields.Boolean(string='Is Transferred', default=False, tracking=True)

    reason = fields.Text(string='Reason', tracking=True)

    @api.onchange('type')
    def onchange_type(self):

        if self.type == 'grn':
            from_location_id_grn = self.env['stock.location'].search([('is_factory_grn_location', '=', True)], limit=1)
            if from_location_id_grn:
                self.from_location_id_grn = from_location_id_grn.id

        elif self.type == 'finished':
            from_location_id_finished = self.env['stock.location'].search([('is_factory_production_location', '=', True)], limit=1)
            if from_location_id_finished:
                self.from_location_id_finished = from_location_id_finished.id

        elif self.type == 'scraping':
            to_location_id_scraping = self.env['stock.location'].search([('is_factory_scrap_location', '=', True)], limit=1)
            if to_location_id_scraping:
                self.to_location_id_scraping = to_location_id_scraping.id


    @api.depends('picking_ids')
    def _compute_picking_count(self):
        for record in self:
            record.picking_count = len(record.picking_ids)

    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].next_by_code('mrp.stock.transfer')
        return super(MrpStockTransfers, self).create(values)


    def load_items(self):

        self.transfer_lines.unlink()

        from_location_id = False
        if self.type == 'grn':
            from_location_id = self.from_location_id_grn
        elif self.type == 'finished':
            from_location_id = self.from_location_id_finished
        elif self.type == 'scraping':
            from_location_id = self.from_location_id_scraping

        if not from_location_id:
            raise UserError(_("Please select a valid source location"))


        stocks = self.env['stock.quant'].search([
            ('location_id', '=', from_location_id.id),
            ('quantity', '>', 0)
        ])
        for s in stocks:
            line_vals = {
                'transfer_id': self.id,
                'product_id': s.product_id.id,
                'quant_id': s.id,
                'on_hand_stock': s.quantity,
                'available_stock': s.quantity - s.reserved_quantity,
            }
            self.transfer_lines.create(line_vals)
        self.state = 'item_loaded'



    def action_confirm(self):

        Picking = self.env['stock.picking']
        Move = self.env['stock.move']
        MoveLine = self.env['stock.move.line']

        from_location_id = False
        to_location_id = False
        if self.type == 'grn':
            from_location_id = self.from_location_id_grn
            to_location_id = self.to_location_id_grn
        elif self.type == 'finished':
            from_location_id = self.from_location_id_finished
            to_location_id = self.to_location_id_finished
        elif self.type == 'scraping':
            from_location_id = self.from_location_id_scraping
            to_location_id = self.to_location_id_scraping

        if not from_location_id:
            raise UserError(_("Please select a valid source location"))

        if not to_location_id:
            raise UserError(_("Please select a valid destination location"))

        if self.type == 'scraping' and not self.reason:
            raise UserError(_("Please provide a reason for the scrap transfer."))


        picking = Picking.create({
            'picking_type_id': self.env.ref('stock.picking_type_internal').id,  # Internal Transfer Type
            'location_id': from_location_id.id,
            'location_dest_id': to_location_id.id,
            'origin': self.name,
        })

        check_is_any_qty = False

        for line in self.transfer_lines:
            if line.quantity > 0:

                if line.quantity > (line.quant_id.quantity - line.quant_id.reserved_quantity):
                    raise UserError(_("Transfer quantity for product '%s' exceeds available stock." % line.product_id.name))

                check_is_any_qty = True

                move = Move.create({
                    'picking_id': picking.id,
                    'name': f"{line.product_id.name} Transfer",
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity,  # Ensure this matches stock.move.line sum
                    'product_uom': line.product_id.uom_po_id.id,
                    'location_id': from_location_id.id,
                    'location_dest_id': to_location_id.id,
                    'state': 'draft',  # Ensures proper reservation
                })

                MoveLine.create({
                    'move_id': move.id,
                    'picking_id': picking.id,
                    'product_id': line.product_id.id,
                    'quantity': line.quantity,
                    'product_uom_id': line.product_id.uom_po_id.id,
                    'location_id': from_location_id.id,
                    'location_dest_id': to_location_id.id,
                    'quant_id': line.quant_id.id,
                    'lot_id': line.quant_id.lot_id and line.quant_id.lot_id.id,
                })

        if not check_is_any_qty:
            raise UserError(_("Please enter a valid quantity for at least one product."))

        picking.action_confirm()
        picking.with_context(skip_expired=True).button_validate()
        self.picking_ids = picking.ids
        self.state = 'completed'



    def action_cancel(self):
        self.state = 'cancel'


    def action_view_pickings(self):
        return {
            'name': 'Related Pickings',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'domain': [('origin', '=', self.name)],  # Filter by request name as origin
            'context': {'create': False}
        }



class ProductionRequestLine(models.Model):
    _name = 'mrp.stock.transfer.line'
    _description = 'Production Request Line'

    transfer_id = fields.Many2one('mrp.stock.transfer', string='Stock Transfer')

    product_id = fields.Many2one('product.product', string='Product')
    quant_id = fields.Many2one('stock.quant', 'Lot/Exp')
    on_hand_stock = fields.Float(string='Stock On Hand', digits = (10,6))
    available_stock = fields.Float(string='Available Qty', digits = (10,6))
    quantity = fields.Float(string='Transfer Qty', digits = (10,6))
