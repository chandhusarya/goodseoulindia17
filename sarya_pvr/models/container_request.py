# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import date_utils
from datetime import timedelta

class ContainerRequest(models.Model):
    _name = 'container.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Container Request'
    _order = 'create_date desc'

    name = fields.Char(string='Request ID', required=True, copy=False, readonly=True,
                       default=lambda self: _('New')) # Auto-generated reference
    remarks = fields.Char('Remarks', required=True)
    pvr_location_id = fields.Many2one('stock.location', string='PVR Location', required=True,
                                       domain=[('usage', '=', 'internal')], # Only internal locations
                                       help="The specific stock location for this PVR.")
    request_date = fields.Datetime(string='Container Requested On', required=True, default=lambda self: fields.Datetime.now())
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'GRN Pending'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], default='draft', string='State', tracking=True)

    request_line_ids = fields.One2many('container.request.line', 'request_id', string='Product Details',
                                       copy=True, auto_join=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company,
                                 readonly=True)
    pvr_master = fields.Many2one('pvr.location.master', string='PVR Master')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('container.request') or _('New')
        result = super(ContainerRequest, self).create(vals_list)
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

    def action_mark_as_received(self):
        if not any(line.received_qty > 0 for line in self.request_line_ids):
            raise UserError(_("Please add Received Qty"))
        self.state = 'done'

    def action_done(self):
        if not any(line.requested_qty > 0 for line in self.request_line_ids):
            raise UserError(_("Please add Requested Qty"))
        self.request_line_ids.filtered(lambda l: l.requested_qty <= 0).unlink()
        self.state = 'pending'



class ContainerRequestLine(models.Model):
    _name = 'container.request.line'
    _description = 'Container Request Line'

    request_id = fields.Many2one('container.request', string='Container Request', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure')

    qty_available_at_pvr = fields.Float(string='Stock on Hand', compute='_compute_qty_available', store=True) # Not stored as it changes
    requested_qty = fields.Float(string='Requested Qty', required=True, default=0.0)
    received_qty = fields.Float(string='Received Qty', required=True, default=0.0)
    pvr_master = fields.Many2one('pvr.location.master', related='request_id.pvr_master')
    state = fields.Selection(string='State', related='request_id.state')

    daily_avg_last_7_days = fields.Float(
        string="Daily Avg Movement(7 days)",
        compute="_compute_daily_avg_last_7_days",
        store=False,
    )
    coverage_days = fields.Float(
        string="Coverage",
        compute="_compute_daily_avg_last_7_days",
        store=False,
    )

    def _compute_daily_avg_last_7_days(self):
        today = fields.Date.today()
        start_date = today - timedelta(days=7)

        for line in self:
            request_lines = self.env["container.request.line"].sudo().search([
                ("product_id", "=", line.product_id.id),
                ("request_id.request_date", ">=", start_date),
                ("request_id.request_date", "<=", today),
                ("request_id.state", "=", "done"),  # only done requests
                ("request_id.pvr_location_id", "=", line.request_id.pvr_location_id.id),  # optional: per PVR
            ])

            total_qty = sum(request_lines.mapped("requested_qty"))
            daily_avg = total_qty / 7.0 if total_qty else 0.0
            line.daily_avg_last_7_days = daily_avg

            # Coverage Calculation
            if daily_avg > 0:
                line.coverage_days = line.qty_available_at_pvr / daily_avg
            else:
                line.coverage_days = 0.0


    @api.onchange('requested_qty')
    def onchange_requested_qty(self):
        for rec in self:
            if rec.request_id.pvr_master.minimum_quantity_required and rec.requested_qty < rec.request_id.pvr_master.minimum_quantity_required:
                raise ValidationError(_("Please Request Minimum %s Quantity" % rec.request_id.pvr_master.minimum_quantity_required))
            rec.received_qty = rec.requested_qty
    #
    @api.depends('product_id', 'request_id.pvr_master')
    def _compute_qty_available(self):
        for line in self:
            management_location = line.request_id.pvr_master.pvr_management_location
            if line.product_id and management_location:
                domain = [
                    ('product_id', '=', line.product_id.id),
                    ('location_id', '=', management_location.id),
                    ('quantity', '>', 0) # Only show positive quantities
                ]
                quants = self.env['stock.quant'].search(domain)
                line.qty_available_at_pvr = sum(q.quantity for q in quants)
            else:
                line.qty_available_at_pvr = 0.0