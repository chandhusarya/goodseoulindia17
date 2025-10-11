# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import date_utils
from datetime import timedelta

class PVRStockRequest(models.Model):
    _name = 'pvr.stock.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'PVR Stock Request'
    _order = 'create_date desc'

    name = fields.Char(string='Request ID', required=True, copy=False, readonly=True,
                       default=lambda self: _('New')) # Auto-generated reference
    pvr_location_id = fields.Many2one('stock.location', string='PVR Location', required=True,
                                       domain=[('usage', '=', 'internal')], # Only internal locations
                                       help="The specific stock location for this PVR.")
    source_location = fields.Many2one('stock.location', string='Source Location', domain=[('usage', '=', 'internal')],
                                       help="Source Location")
    request_date = fields.Date(string='Request Date', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('manager_approval', 'Waiting Approval'),
        ('approved', 'Approved'),
        ('pending', 'GRN Pending'),
        ('exception', 'Exception'),
        ('completed', 'Completed'),
        ('cancel', 'Cancelled'),
    ], default='draft', string='State', tracking=True)

    request_line_ids = fields.One2many('pvr.stock.request.line', 'request_id', string='Request Lines',
                                       copy=True, auto_join=True)

    # --- Compute Fields (Optional but useful) ---
    total_requested_qty = fields.Float(string='Total Requested Qty', compute='_compute_total_requested_qty', store=True)
    is_draft = fields.Boolean(compute='_compute_is_draft', string="Is Draft")
    is_requested = fields.Boolean(compute='_compute_is_requested', string="Is Requested")
    is_transfered = fields.Boolean(
        string='Transfered',
        default=False, copy=False)
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company,
                                 readonly=True)
    pvr_master = fields.Many2one('pvr.location.master', string='PVR Master')
    local_purchase_ids = fields.One2many(
        "local.purchase",
        "pvr_request_id",
        string="LPOs",
        readonly=True,
    )

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
                res['source_location'] = pvr_master.source_location_id.id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('pvr.stock.request') or _('New')
        result = super(PVRStockRequest, self).create(vals_list)
        return result

    @api.depends('request_line_ids.requested_qty')
    def _compute_total_requested_qty(self):
        for record in self:
            record.total_requested_qty = sum(line.requested_qty for line in record.request_line_ids)

    @api.depends('state')
    def _compute_is_draft(self):
        for rec in self:
            rec.is_draft = rec.state == 'draft'

    @api.depends('state')
    def _compute_is_requested(self):
        for rec in self:
            rec.is_requested = rec.state == 'requested'

    # --- Button Actions ---

    def action_request(self):
        if not any(line.requested_qty > 0 for line in self.request_line_ids):
            raise UserError("Please Request for any one item")

        # for line in self.request_line_ids:
        self.request_line_ids.filtered(lambda l: l.requested_qty <= 0).unlink()

        users = self.sudo().env.ref('sarya_pvr.can_approve_pvr_stock_req').users
        email_to = ""
        for usr in users:
            if usr.partner_id.email:
                if not email_to:
                    email_to = usr.partner_id.email
                else:
                    email_to = email_to + ', ' + usr.partner_id.email

        main_content = {
            'subject': _('PVR Stock Request: No. %s approval request' % self.name),
            'author_id': self.env.user.partner_id.id,
            'body_html': 'Hi,<br><br>PVR Stock request %s is waiting for your approval.' % self.name,
            'email_to': email_to,
        }
        self.env['mail.mail'].sudo().create(main_content).send()
        self.state = 'manager_approval'

    def action_approve(self):
        has_vendor = any(line.lpo_vendor_id and line.lpo_qty > 0 for line in self.request_line_ids)

        if has_vendor:
            PurchaseOrder = self.env["local.purchase"]
            po_map = {}  # vendor -> PO

            for line in self.request_line_ids.filtered(lambda l: l.lpo_vendor_id):
                if line.lpo_qty > 0:
                    vendor = line.lpo_vendor_id

                    if vendor not in po_map:
                        po_vals = {
                            "vendor_id": vendor.id,
                            "purchase_type": 'normal',
                            "date": fields.Date.today(),
                            "pvr_request_id": self.id,  # link request to PO
                        }
                        po_map[vendor] = PurchaseOrder.sudo().create(po_vals)

                    # Add PO line
                    taxes = line.product_id.supplier_taxes_id
                    self.env["local.purchase.line"].sudo().create({
                        "local_purchase_id": po_map[vendor].id,
                        "product_id": line.product_id.id,
                        "name": line.product_id.name,
                        "qty": line.lpo_qty,
                        "packaging_id": line.packaging_id.id,
                        "tax_ids": [(6, 0, taxes.ids)],
                    })
            self.message_post(
                body=f"LPO(s) created for vendors: {', '.join(v.name for v in po_map.keys())}"
            )
            self.state = "pending"

        else:
            self.action_create_pickings()
            users = self.env.ref("sarya_pvr.can_transfer_pvr_stock_req").users
            email_to = ",".join(u.partner_id.email for u in users if u.partner_id.email)

            if email_to:
                main_content = {
                    "subject": _("PVR Stock Request: No. %s is Approved" % self.name),
                    "author_id": self.env.user.partner_id.id,
                    "body_html": f"Hi,<br><br>PVR Stock request {self.name} is approved. Please transfer the materials",
                    "email_to": email_to,
                }
                self.env["mail.mail"].sudo().create(main_content).send()

    purchase_order_count = fields.Integer(
        string="Purchase Orders", compute="_compute_purchase_order_count"
    )

    def _compute_purchase_order_count(self):
        for rec in self:
            rec.purchase_order_count = len(rec.local_purchase_ids)

    def action_view_purchase_orders(self):
        self.ensure_one()
        action = self.env.ref("sarya_factory.local_purchase_factory_act_window").sudo().read()[0]
        if len(self.local_purchase_ids) > 1:
            action["domain"] = [("id", "in", self.local_purchase_ids.ids)]
            action["view_mode"] = "tree,form"
        elif len(self.local_purchase_ids) == 1:
            form_view = [(self.env.ref("sarya_factory.local_purchase_form_view_factory").id, "form")]
            action["views"] = form_view
            action["res_id"] = self.local_purchase_ids.id
        else:
            action["domain"] = [("id", "in", [])]

        return action

    def action_recheck_grn(self):
        self.state = 'pending'

    def action_cancel(self):
        self.state = 'cancel'

    def action_create_pickings(self):
        """
        Creates stock pickings based on the requested items.
        """
        for request in self:
            pvr = request.pvr_master
            source_location = request.source_location
            destination_location = pvr.temp_location_id # Example: 'Stock' location in WH

            if not source_location or not destination_location:
                raise UserError(_("Source or Destination Location is not defined. Please check PVR Location and Odoo's default warehouse configuration."))

            moves_vals = []
            for line in request.request_line_ids:
                for detail in line.detail_ids:
                    if line.requested_qty > 0:
                        move_vals = {
                            'product_id': line.product_id.id,
                            'name': f"PVR Req: {request.name} - {line.product_id.display_name}",
                            'product_uom_qty': detail.quantity,
                            'product_uom': line.product_uom_id.id,
                            'location_id': source_location.id,
                            'location_dest_id': destination_location.id,
                            'origin': request.name,
                            'state': 'draft',
                        }

                        if detail:
                            move_vals['picking_type_id'] = self.env.ref('stock.picking_type_out').id
                            move_vals['move_line_ids'] = [(0, 0, {
                                'product_id': line.product_id.id,
                                'quant_id': detail.quant_id.id,
                                'lot_id': detail.quant_id.lot_id and detail.quant_id.lot_id.id,
                                'quantity': detail.quantity,
                                'product_uom_id': detail.product_uom_id.id,
                                'location_id': source_location.id,
                                'location_dest_id': destination_location.id,
                                'state': 'draft',
                            })]
                            moves_vals.append((0, 0, move_vals))

                        else:
                            move_vals['picking_type_id'] = self.env.ref('stock.picking_type_out').id
                            moves_vals.append((0, 0, move_vals))

            if not moves_vals:
                raise UserError(_("No products with quantity to request found in this request. Please Add the Details"))

            picking_vals = {
                'picking_type_id': self.env.ref('stock.picking_type_out').id, # Assuming outgoing picking type
                'location_id': source_location.id, # Source for the picking itself
                'location_dest_id': destination_location.id, # Destination for the picking
                'origin': request.name,
                'move_ids': moves_vals,
            }
            picking = self.env['stock.picking'].create(picking_vals)

            request.write({'picking_ids': [(4, picking.id)],
                           'state': 'pending'}) # Assumes you add picking_ids field
            picking.action_confirm()
            picking.button_validate()

    def action_view_pickings(self):
        return {
            'name': 'Related Pickings',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'domain': [('origin', '=', self.name)],  # Filter by request name as origin
            'context': {'create': False}
        }

    def action_done(self):
        """ Marks the request as completed (assuming pickings were handled) """
        for request in self:
            if request.state == 'picking_created':
                request.state = 'done'
            else:
                raise UserError(_("You can only complete a request that has had pickings created."))
        return True

    def action_cancel(self):
        """ Cancels the stock request """
        for request in self:
            if request.state not in ('done', 'cancel'):
                request.state = 'cancel'
        return True

    def action_accept(self):
        """
        Creates stock pickings based on the requested items.
        """
        for request in self:
            if any(line.requested_qty != detail.quantity for line in self.request_line_ids for detail in line.detail_ids):
                # detferd
                request.state = 'exception'
                users = self.sudo().env.ref('sarya_pvr.can_transfer_pvr_stock_req').users
                email_to = ""
                for usr in users:
                    if usr.partner_id.email:
                        if not email_to:
                            email_to = usr.partner_id.email
                        else:
                            email_to = email_to + ', ' + usr.partner_id.email

                main_content = {
                    'subject': _('PVR Stock Request: No. %s has ran into Exception State' % self.name),
                    'author_id': self.env.user.partner_id.id,
                    'body_html': 'Hi,<br><br>PVR Stock request %s has ran into Exception State. Please look into it and and check for the quantity accepted' % self.name,
                    'email_to': email_to,
                }
                self.env['mail.mail'].sudo().create(main_content).send()
            else:
                pvr = request.pvr_master
                source_location = pvr.temp_location_id
                destination_location = request.pvr_location_id # Example: 'Stock' location in WH

                if not source_location or not destination_location:
                    raise UserError(_("Source or Destination Location is not defined. Please check PVR Location and Odoo's default warehouse configuration."))

                moves_vals = []
                for line in request.request_line_ids.sudo():
                    for detail in line.detail_ids:

                        if line.requested_qty > 0:
                            move_vals = {
                                'product_id': line.product_id.id,
                                'name': f"PVR Req: {request.name} - {line.product_id.display_name}",
                                'product_uom_qty': detail.quantity,
                                'product_uom': line.product_uom_id.id,
                                'location_id': source_location.id,
                                'location_dest_id': destination_location.id,
                                'origin': request.name,
                                'state': 'draft',
                            }

                            if detail:
                                move_vals['picking_type_id'] = self.sudo().env.ref('stock.picking_type_internal').id
                                move_vals['move_line_ids'] = [(0, 0, {
                                    'product_id': line.product_id.id,
                                    # 'quant_id': detail.quant_id.id,
                                    'lot_id': detail.lot_id and detail.lot_id.id,
                                    'quantity': detail.quantity,
                                    'product_uom_id': detail.product_uom_id.id,
                                    'location_id': source_location.id,
                                    'location_dest_id': destination_location.id,
                                    'state': 'draft',
                                })]
                                moves_vals.append((0, 0, move_vals))

                            else:
                                move_vals['picking_type_id'] = self.sudo().env.ref('stock.picking_type_internal').id
                                moves_vals.append((0, 0, move_vals))

                if not moves_vals:
                    raise UserError(_("No products with quantity to request found in this request. Please Add the Details"))

                picking_vals = {
                    'picking_type_id': self.sudo().env.ref('stock.picking_type_internal').id, # Assuming outgoing picking type
                    'location_id': source_location.id, # Source for the picking itself
                    'location_dest_id': destination_location.id, # Destination for the picking
                    'origin': request.name,
                    'move_ids': moves_vals,
                }

                picking = self.env['stock.picking'].sudo().create(picking_vals)

                request.sudo().write({'picking_ids': [(4, picking.id)],
                               'state': 'completed'}) # Assumes you add picking_ids field
                picking.action_confirm()
                picking.button_validate()


    picking_ids = fields.One2many('stock.picking', 'pvr_request_id', string='Stock Pickings', readonly=True)


class PVRStockRequestLine(models.Model):
    _name = 'pvr.stock.request.line'
    _description = 'PVR Stock Request Line'

    request_id = fields.Many2one('pvr.stock.request', string='PVR Request', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure')

    qty_available_at_pvr = fields.Float(string='Qty in PVR', compute='_compute_qty_available', store=False) # Not stored as it changes
    requested_qty = fields.Float(string='Requested Qty', required=True, default=0.0)
    notes = fields.Text(string='Notes')
    packaging_id = fields.Many2one(comodel_name='product.packaging', string='Req Packaging',
                                   domain="[('product_id', '=', product_id)]")
    primary_packaging_id = fields.Many2one(comodel_name='product.packaging', string='Primary Packaging',
                                           domain="[('primary_unit', '=', True), ('product_id', '=', product_id)]")
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial Number',
                             domain="[('product_id', '=', product_id)]",
                             help="Select a specific lot or serial number available at the Source Location.")
    available_lot_ids = fields.Many2many('stock.lot', compute='_compute_available_lots')
    requested_qty_primary = fields.Float(string='Req Qty Primary')
    pvr_location_id = fields.Many2one('stock.location', string='PVR Location', related='request_id.pvr_location_id',
                                          domain=[('usage', '=', 'internal')])
    transferred_qty = fields.Float(string='Approved Qty', compute='_compute_transferred_qty')
    detail_ids = fields.One2many('pvr.stock.request.line.details', 'request_line_id', string='Request Lines')
    is_transfered = fields.Boolean(related='request_id.is_transfered')
    source_location_id = fields.Many2one('stock.location', string='Source Location', related='request_id.source_location')
    pvr_master = fields.Many2one('pvr.location.master', related='request_id.pvr_master')
    allowed_product_ids = fields.Many2many(
        'product.product',
        compute='_compute_allowed_products',
        store=False
    )
    state = fields.Selection(string='State', related='request_id.state')
    lpo_vendor_id = fields.Many2one(
        "res.partner",
        string="LPO Vendor",
        domain=[("supplier_rank", ">", 0)],  # only vendors
        help="Vendor to purchase this product from",
    )
    lpo_qty = fields.Float(string="LPO Quantity")

    @api.onchange('pvr_master')
    def onchange_pvr_master_set_location(self):
        for rec in self:
            rec.pvr_location_id = rec.pvr_master.location_id

    @api.depends('request_id')
    def _compute_allowed_products(self):
        for line in self:
            line.allowed_product_ids = self.request_id.sudo().pvr_master.allowed_product_ids if self.request_id.pvr_master else False

    @api.depends('detail_ids')
    def _compute_transferred_qty(self):
        for line in self:
            total_quantity = 0
            for detail in line.detail_ids:
                total_quantity += detail.quantity
            line.transferred_qty = total_quantity

    @api.onchange('requested_qty')
    def onchange_requested_qty(self):
        if self.requested_qty > 0:
            self.requested_qty_primary = self.requested_qty * self.packaging_id.qty
            self.onchange_product()

    @api.depends('product_id', 'request_id.source_location')
    def _compute_available_lots(self):
        for rec in self:
            source_location = rec.request_id.source_location
            lots = self.env['stock.quant'].search([
                ('product_id', '=', rec.product_id.id),
                ('location_id', '=', source_location.id),
                ('quantity', '>', 0),
                ('lot_id', '!=', False),
            ])
            rec.available_lot_ids = lots.mapped('lot_id')

    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id and self.product_id.seller_ids:
            self.lpo_vendor_id = self.product_id.seller_ids[0].partner_id.id
        primary_packaging_id = False
        on_hand_qty = 0
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id
            packaging = self.env['product.packaging'].search([
                ('product_id', '=', self.product_id.id), ('primary_unit', '=', True)], limit=1)
            primary_packaging_id = packaging and packaging.id

            quants = self.env['stock.quant'].search([('location_id', 'child_of', self.request_id.pvr_location_id.id),
                                                     ('product_id', '=', self.product_id.id)
                                                     ])
            for q in quants:
                on_hand_qty += q.quantity

        self.packaging_id = primary_packaging_id
        self.qty_available_at_pvr = on_hand_qty

    def action_open_line_details(self):
        """ Open the form view of Material Request Line with its details """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'PVR Stock Request Line',
            'res_model': 'pvr.stock.request.line',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',  # Opens in a popup
        }


    @api.depends('product_id', 'request_id.pvr_location_id')
    def _compute_qty_available(self):
        for line in self:
            if line.product_id and line.request_id.pvr_location_id:
                domain = [
                    ('product_id', '=', line.product_id.id),
                    ('location_id', '=', line.request_id.pvr_location_id.id),
                    ('quantity', '>', 0) # Only show positive quantities
                ]
                quants = self.env['stock.quant'].search(domain)
                line.qty_available_at_pvr = sum(q.quantity for q in quants)
            else:
                line.qty_available_at_pvr = 0.0

    @api.constrains('requested_qty')
    def _check_requested_qty(self):
        for line in self:
            if line.requested_qty < 0:
                raise ValidationError(_("Requested quantity cannot be negative."))

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
            request_lines = self.env["pvr.stock.request.line"].sudo().search([
                ("product_id", "=", line.product_id.id),
                ("request_id.request_date", ">=", start_date),
                ("request_id.request_date", "<=", today),
                ("request_id.state", "=", "completed"),  # only done requests
                ("request_id.pvr_location_id", "=", line.request_id.pvr_location_id.id),  # optional: per PVR
            ])

            total_qty = sum(request_lines.mapped("requested_qty"))
            daily_avg = total_qty / 7.0 if total_qty else 0.0
            line.daily_avg_last_7_days = daily_avg

            if daily_avg > 0:
                line.coverage_days = line.qty_available_at_pvr / daily_avg
            else:
                line.coverage_days = 0.0

class PVRRequestLineDetails(models.Model):
    _name = 'pvr.stock.request.line.details'
    _description = 'PVR Stock Request Line Details'

    request_id = fields.Many2one('pvr.stock.request', string='Stock Request')
    request_line_id = fields.Many2one('pvr.stock.request.line', string='Stock Request Line')
    product_id = fields.Many2one('product.product', string='Product')
    pvr_location_id = fields.Many2one('stock.location', string='PVR Location', related='request_id.pvr_location_id')
    source_location_id = fields.Many2one('stock.location', string='Source Location')
    quant_id = fields.Many2one('stock.quant', 'Lot/Expiry')
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure')
    total_stock = fields.Float(string='Total Stock')
    available_stock = fields.Float(string='Available Stock')
    quantity = fields.Float(string='Quantity')
    lot_id = fields.Many2one('stock.lot', 'Lot Number', related='quant_id.lot_id')

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

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    pvr_request_id = fields.Many2one('pvr.stock.request', string='PVR Stock Request')
    pvr_lpo_request_id = fields.Many2one('local.purchase', string='PVR Local Purchase')
    pvr_transfer_id = fields.Many2one('container.transfer.pvr', string='PVR Transfer')

class LocalPurchase(models.Model):
    _inherit = 'local.purchase'

    pvr_request_id = fields.Many2one(
        "pvr.stock.request",
        string="PVR Stock Request",
        ondelete="set null",
    )

class PVRStockQuant(models.Model):
    _inherit = 'stock.quant'

class PVRIrSequence(models.Model):
    _inherit = 'ir.sequence'

class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'

class ProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'