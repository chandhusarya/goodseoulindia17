# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import date_utils

class ClosingSession(models.Model):
    _name = 'closing.session'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Closing Session'
    _order = 'create_date desc'

    name = fields.Char(string='Request ID', required=True, copy=False, readonly=True,
                       default=lambda self: _('New')) # Auto-generated reference
    remarks = fields.Char('Remarks', required=True)
    pvr_location_id = fields.Many2one('stock.location', string='PVR Location', required=True,
                                       domain=[('usage', '=', 'internal')], # Only internal locations
                                       help="The specific stock location for this PVR.")
    closing_datetime = fields.Datetime(
        string="Closing Time",
        required=True, default=lambda self: fields.Datetime.now()
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], default='draft', string='State', tracking=True)

    request_line_ids = fields.One2many('container.closing.session.line', 'request_id', string='Product Details',
                                       copy=True, auto_join=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company,
                                 readonly=True)
    pvr_master = fields.Many2one('pvr.location.master', string='PVR Master')
    has_damaged_qty = fields.Boolean(
        string="Has Damaged Products",
        compute="_compute_has_damaged_qty"
    )
    is_scrapped = fields.Boolean('Is Scrapped')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('closing.session') or _('New')
        result = super(ClosingSession, self).create(vals_list)
        return result

    def _compute_has_damaged_qty(self):
        for rec in self:
            rec.has_damaged_qty = any(line.damaged_qty > 0 for line in rec.request_line_ids)

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

    def action_done(self):
        if not any(line.returned_qty > 0 for line in self.request_line_ids):
            raise UserError(_("Please add Returned Qty"))
        self.action_scrap_damaged()
        self.state = 'done'

    def action_scrap_damaged(self):
        StockScrap = self.env["stock.scrap"].sudo()
        for rec in self:
            for line in rec.request_line_ids.filtered(lambda l: l.damaged_qty > 0):
                # Find a quant for this product in the PVR management location
                quant = self.env["stock.quant"].search([
                    ("product_id", "=", line.product_id.id),
                    ("location_id", "=", rec.pvr_master.pvr_management_location.id),
                    ("quantity", ">", 0),
                ], limit=1)

                scrap_vals = {
                    "product_id": line.product_id.id,
                    "scrap_qty": line.damaged_qty,
                    "company_id": rec.company_id.id,
                    "location_id": rec.pvr_master.pvr_management_location.id,
                }

                if quant and quant.lot_id:
                    scrap_vals["lot_id"] = quant.lot_id.id

                scrap_id = StockScrap.create(scrap_vals)
                scrap_id.sudo().action_validate()
                rec.is_scrapped = True

    def action_go_home(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/my/home',
            'target': 'self',
        }


class ContainerClosingSessionLine(models.Model):
    _name = 'container.closing.session.line'
    _description = 'Container Closing Session Line'

    request_id = fields.Many2one('closing.session', string='Closing Request', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure')

    qty_available_at_pvr = fields.Float(string='Stock Received', readonly=True,)
    damaged_qty = fields.Float(string='Damaged Qty', required=True, default=0.0)
    returned_qty = fields.Float(string='Closing Stock on Hand', required=True, default=0.0)
    pvr_master = fields.Many2one('pvr.location.master', related='request_id.pvr_master')
    state = fields.Selection(string='State', related='request_id.state')
    damage_reason = fields.Char('Damaged Reason')