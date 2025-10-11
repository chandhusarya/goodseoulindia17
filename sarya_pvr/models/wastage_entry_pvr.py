# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import date_utils

class PvrWastageEntry(models.Model):
    _name = "pvr.wastage.entry"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Wastage Entry"
    _order = 'create_date desc'

    name = fields.Char(default=lambda self: _('New'))
    date = fields.Datetime(default=fields.Datetime.now)
    # location_id = fields.Many2one("stock.location", required=True, string="Location")
    line_ids = fields.One2many("pvr.wastage.entry.line", "entry_id", string="Lines")
    pvr_master = fields.Many2one('pvr.location.master', string='PVR Master')
    pvr_location_id = fields.Many2one('stock.location', string='PVR Location', required=True,
                                       domain=[('usage', '=', 'internal')])
    state = fields.Selection([
        ('draft', 'Draft'),
        ('manager_approval', 'Waiting Approval'),
        # ('approved', 'Approved'),
        ('completed', 'Completed'),
        ('cancel', 'Cancelled'),
    ], default='draft', string='State', tracking=True)
    remarks = fields.Char('Remarks', required=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company,
                                 readonly=True)

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
                res['pvr_master'] = pvr_master.id # default first allowed
                # res['source_location'] = pvr_master.source_location_id.id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('pvr.wastage.entry') or _('New')
        result = super(PvrWastageEntry, self).create(vals_list)
        return result

    def action_send_for_approval(self):
        if not any(line.wastage_qty > 0 for line in self.line_ids):
            raise UserError("Please Add Wastage Qty for any one item")

        # for line in self.request_line_ids:
        self.line_ids.filtered(lambda l: l.wastage_qty <= 0).unlink()

        users = self.sudo().env.ref('sarya_pvr.can_approve_pvr_stock_req').users
        email_to = ""
        for usr in users:
            if usr.partner_id.email:
                if not email_to:
                    email_to = usr.partner_id.email
                else:
                    email_to = email_to + ', ' + usr.partner_id.email

        main_content = {
            'subject': _('PVR Wastage Entry: No. %s approval request' % self.name),
            'author_id': self.env.user.partner_id.id,
            'body_html': 'Hi,<br><br>PVR Wastage Entry %s is waiting for your approval.' % self.name,
            'email_to': email_to,
        }
        self.env['mail.mail'].sudo().create(main_content).send()
        self.state = 'manager_approval'

    def action_cancel(self):
        self.state = 'cancel'


    def action_approve(self):
        Scrap = self.env["stock.scrap"].sudo()
        Quant = self.env["stock.quant"].sudo()

        for rec in self:
            for line in rec.line_ids.filtered(lambda l: l.wastage_qty > 0):
                qty_to_scrap = line.wastage_qty

                quants = Quant.search([
                    ("product_id", "=", line.product_id.id),
                    ("location_id", "in", [rec.pvr_location_id.id, rec.pvr_master.pvr_management_location.id]),
                    ("quantity", ">", 0),
                ], order="in_date asc")

                for quant in quants:
                    if qty_to_scrap <= 0:
                        break

                    scrap_qty = min(qty_to_scrap, quant.quantity)
                    print('scrap_qty', scrap_qty)
                    # rsdr
                    scrap_id = Scrap.create({
                        "product_id": line.product_id.id,
                        "scrap_qty": scrap_qty,
                        "company_id": rec.env.company.id,
                        "location_id": quant.location_id.id,
                        "lot_id": quant.lot_id.id if quant.lot_id else False,
                    })
                    print('scrap_id', scrap_id)
                    scrap_id.action_validate()

                    qty_to_scrap -= scrap_qty

                if qty_to_scrap > 0:
                    raise UserError(_("Not enough stock to scrap %s for product %s") %
                                    (line.wastage_qty, line.product_id.display_name))
            rec.state = 'completed'

class PvrWastageEntryLine(models.Model):
    _name = "pvr.wastage.entry.line"
    _description = "Wastage Entry Line"

    entry_id = fields.Many2one("pvr.wastage.entry", required=True, ondelete="cascade")
    product_id = fields.Many2one("product.product", required=True)
    total_stock = fields.Float(compute="_compute_total_stock", store=False)
    wastage_qty = fields.Float(string="Wastage Quantity")
    packaging_id = fields.Many2one(comodel_name='product.packaging', string='Packaging',
                                   domain="[('product_id', '=', product_id)]")

    @api.depends("product_id", "entry_id.pvr_location_id")
    def _compute_total_stock(self):
        for line in self:
            if line.product_id and line.entry_id.pvr_location_id:
                quants = self.env["stock.quant"].search(
                    [("product_id", "=", line.product_id.id),
                     ("location_id", "in", [line.entry_id.pvr_location_id.id, line.entry_id.pvr_master.pvr_management_location.id])]
                )
                line.total_stock = sum(quants.mapped("quantity"))
            else:
                line.total_stock = 0.0

    @api.onchange('product_id')
    def onchange_product(self):
        primary_packaging_id = False
        if self.product_id:
            # self.product_uom_id = self.product_id.uom_id
            packaging = self.env['product.packaging'].search([
                ('product_id', '=', self.product_id.id), ('primary_unit', '=', True)], limit=1)
            primary_packaging_id = packaging and packaging.id
        self.packaging_id = primary_packaging_id

