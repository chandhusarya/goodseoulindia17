# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import date_utils

class ContainerTransferPvr(models.Model):
    _name = 'container.transfer.pvr'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Container Transfer PVR'
    _order = 'create_date desc'

    name = fields.Char(string='Request ID', required=True, copy=False, readonly=True,
                       default=lambda self: _('New')) # Auto-generated reference
    remarks = fields.Char('Remarks', required=True)
    pvr_location_id = fields.Many2one('stock.location', string='PVR Location', required=True,
                                       domain=[('usage', '=', 'internal')])
    request_date = fields.Datetime(string='Transferred On', required=True, default=lambda self: fields.Datetime.now())
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], default='draft', string='State', tracking=True)

    request_line_ids = fields.One2many('container.transfer.line', 'container_transfer_id', string='Container Details',
                                       copy=True, auto_join=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company,
                                 readonly=True)
    pvr_master = fields.Many2one('pvr.location.master', string='PVR Master')
    picking_ids = fields.One2many('stock.picking', 'pvr_transfer_id', string='Stock Pickings', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('container.transfer') or _('New')
        result = super(ContainerTransferPvr, self).create(vals_list)
        return result


    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        user = self.env.user
        pvr_master = self.env['pvr.location.master'].sudo().search(
            [('allowed_user_ids', 'in', user.id)], limit=1)
        if not pvr_master:
            raise UserError(_("Please Configure PVR Location Master"))

        if pvr_master:
            if 'pvr_location_id' in fields_list:
                res['pvr_location_id'] = pvr_master.location_id.id  # default first allowed
                res['pvr_master'] = pvr_master.id  # default first allowed
        return res

    def action_transfer(self):
        if not any(line.requested_qty > 0 for line in self.request_line_ids):
            raise UserError(_("Please add Quantity"))
        for request in self:
            pvr = request.pvr_master
            source_location = request.pvr_location_id
            destination_location = pvr.pvr_management_location # Example: 'Stock' location in WH

            if not source_location or not destination_location:
                raise UserError(_("Source or Destination Location is not defined. Please check PVR Location and Odoo's default warehouse configuration."))

            # Group products by product ID to avoid duplicate moves
            moves_vals = []
            for line in request.request_line_ids:
                if line.requested_qty > 0:
                    move_vals = {
                        'product_id': line.product_id.id,
                        'name': f"PVR Req: {request.name} - {line.product_id.display_name}",
                        'product_uom_qty': line.requested_qty,
                        'location_id': source_location.id,
                        'location_dest_id': destination_location.id,
                        'origin': request.name,
                    }
                    moves_vals.append((0, 0, move_vals))

            if not moves_vals:
                raise UserError(_("No products with quantity to request found in this request. Please Add the Details"))

            # Create a single stock picking for all these moves
            picking_vals = {
                'picking_type_id': self.env.ref('stock.picking_type_out').id, # Assuming outgoing picking type
                'location_id': source_location.id, # Source for the picking itself
                'location_dest_id': destination_location.id, # Destination for the picking
                'origin': request.name,
                'move_ids': moves_vals,
            }

            picking = self.env['stock.picking'].sudo().create(picking_vals)

            request.write({'picking_ids': [(4, picking.id)],
                           'state': 'done'}) # Assumes you add picking_ids field
            picking.sudo().action_confirm()
            picking.sudo().button_validate()

    def action_view_pickings(self):
        return {
            'name': 'Related Pickings',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'domain': [('origin', '=', self.name)],  # Filter by request name as origin
            'context': {'create': False}
        }



class ContainerTransferLine(models.Model):
    _name = 'container.transfer.line'
    _description = 'Container Transfer Line'

    container_transfer_id = fields.Many2one('container.transfer.pvr', string='Container Transfer', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure')

    qty_available_at_pvr = fields.Float(string='Available', compute='_compute_qty_available', store=False) # Not stored as it changes
    requested_qty = fields.Float(string='Quantity', required=True, default=0.0)
    pvr_master = fields.Many2one('pvr.location.master', related='container_transfer_id.pvr_master')
    state = fields.Selection(string='State', related='container_transfer_id.state')
    packaging_id = fields.Many2one(comodel_name='product.packaging', string='Packaging/Uom',
                                   domain="[('product_id', '=', product_id)]")
    
    @api.onchange('product_id')
    def onchange_product(self):
        primary_packaging_id = False
        if self.product_id:
            packaging = self.env['product.packaging'].search([
                ('product_id', '=', self.product_id.id), ('primary_unit', '=', True)], limit=1)
            primary_packaging_id = packaging and packaging.id

        self.packaging_id = primary_packaging_id

    @api.depends('product_id', 'container_transfer_id.pvr_location_id')
    def _compute_qty_available(self):
        for line in self:
            if line.product_id and line.container_transfer_id.pvr_location_id:
                domain = [
                    ('product_id', '=', line.product_id.id),
                    ('location_id', '=', line.container_transfer_id.pvr_location_id.id),
                    ('quantity', '>', 0) # Only show positive quantities
                ]
                quants = self.env['stock.quant'].search(domain)
                line.qty_available_at_pvr = sum(q.quantity for q in quants)
            else:
                line.qty_available_at_pvr = 0.0