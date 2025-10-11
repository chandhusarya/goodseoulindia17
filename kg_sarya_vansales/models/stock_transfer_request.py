# Copyright 2017-2020 ForgeFlow, S.L.

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.tools import float_compare


class StockTransferRequest(models.Model):
    _name = "stock.transfer.request"
    _description = "Stock Transfer Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    def get_default_location(self):
        vehicle_id = self.env['user.vehicle'].sudo().search([('driver_id', '=', self.env.user.id)], limit=1)
        location = vehicle_id.location_id.id
        return location

    def get_default_van_main_location(self):
        vehicle_id = self.env['user.vehicle'].sudo().search([('driver_id', '=', self.env.user.id)], limit=1)
        if vehicle_id.stock_for_load_request:
            return vehicle_id.stock_for_load_request.id
        location = self.env['stock.location'].search([('name', '=', 'Van Sales')], limit=1)
        return location and location.id or False


    def get_default_vehicle(self):
        vehicle_id = self.env['user.vehicle'].sudo().search([('driver_id', '=', self.env.user.id)], limit=1)
        return vehicle_id.id

    name = fields.Char('Reference #', copy=False, readonly=True)
    state = fields.Selection(
        selection=[("draft", "Draft"),
                   ("request", "Requested"),
                   ("approve", "Approved"),
                   ("reject", "Rejected"),
                   ("done", "Accepted"),
                   ("cancel", "Cancelled")],
        string="Status", copy=False, default="draft",index=True, readonly=True, tracking=True)
    user_id = fields.Many2one("res.users", "Requested by", required=True, tracking=True,
                              default=lambda self: self.env.user.id)
    expected_date = fields.Datetime("Loading Date", default=fields.Datetime.now, index=True, required=True,
                                    help="Date when you expect to receive the goods.", )

    location_id = fields.Many2one("stock.location",
                                  domain="[('id', '=', False), ('usage', '=', 'internal')]",
                                  required=True, default=get_default_location)

    van_main_location_id = fields.Many2one("stock.location",
                                  domain="[('id', '=', False), ('usage', '=', 'internal')]",
                                  required=True, default=get_default_van_main_location)

    vehicle_id = fields.Many2one('user.vehicle', 'Vehicle', default=get_default_vehicle)

    company_id = fields.Many2one("res.company", default=lambda self: self.env.company.id)
    line_ids = fields.One2many('stock.transfer.request.line', 'request_id', string='Lines', copy=True, auto_join=True)
    picking_ids = fields.Many2many("stock.picking", string="Transfers", copy=False)
    picking_count = fields.Integer('Transfers', compute='compute_picking', store=True)
    notes = fields.Text('Additional Notes')

    _sql_constraints = [("name_uniq", "unique(name, company_id)", "Stock Request reference must be unique per company.")]


    def view_current_stock(self):
        action = self.env.ref("cha_sarya_vansales_app.vansales_location_open_quants").sudo().read()[0]
        action['domain'] = [('location_id', '=', self.van_main_location_id.id)]
        action["views"] = [(self.env.ref("cha_sarya_vansales_app.vansales_view_stock_quant_tree").id, "tree")]
        return action

    @api.depends('picking_ids')
    def compute_picking(self):
        for rec in self:
            rec.picking_count = len(rec.picking_ids.filtered(lambda pick: pick.state != 'cancel'))

    def action_request(self):
        self.write({"state": "request"})
        self.sudo().mail_notification_for_request()

    def mail_notification_for_request(self):

        mail_content = "  Hello,<br>Please process load request from vehicle " + str(self.vehicle_id.name) +\
                       " and Request Number is " + str(self.name)


        users = self.env.ref('cha_sarya_vansales_app.group_receive_load_request_email_notification').users
        email_to = ""
        for usr in users:
            if usr.partner_id.email:
                if not email_to:
                    email_to = usr.partner_id.email
                else:
                    email_to = email_to + ', ' + usr.partner_id.email

        main_content = {
            'subject': _('Load Request from %s' % (self.user_id.name)),
            'author_id': self.env.user.partner_id.id,
            'body_html': mail_content,
            'email_to': email_to,
        }
        self.env['mail.mail'].create(main_content).send()

    def action_approve(self):
        self.create_picking()
        self.write({"state": "approve"})

    def action_reject(self):
        self.write({"state": "reject"})

    def action_draft(self):
        self.write({"state": "draft"})

    def action_cancel(self):
        if self.picking_ids:
            self.sudo().picking_ids.action_cancel()
        self.write({"state": "cancel"})

    def _prepare_picking(self, picking_type_id, location_id, location_dest_id):
        vals = {
            'picking_type_id': picking_type_id.id,
            'user_id': False,
            'date': self.expected_date,
            'origin': self.name,
            'location_dest_id': location_dest_id,
            'location_id': location_id,
            'company_id': self.company_id.id,
            'scheduled_date' : self.expected_date,
        }
        return vals

    def create_picking(self):
        StockPicking = self.env['stock.picking']
        picking_type_id = self.env['stock.picking.type'].search([('name', '=', 'Internal Transfers')], limit=1)
        if not picking_type_id:
            raise UserError(_("Internal Transfers operation type is not found in system"))

        for request in self:
                location_dest_id = self.vehicle_id.counterpart_location_id.id
                location_id = self.van_main_location_id.id
                res = request._prepare_picking(picking_type_id, location_id, location_dest_id)
                picking = StockPicking.create(res)
                moves = request.line_ids._create_stock_moves(picking, picking_type_id, location_id, location_dest_id)
                moves = moves._action_confirm()
                moves._action_assign()

                request.picking_ids |= picking

        return True

    def action_view_transfer(self):
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")
        pickings = self.mapped("picking_ids")
        if len(pickings) > 1:
            action["domain"] = [("id", "in", pickings.ids)]
        elif pickings:
            action["views"] = [(self.env.ref("stock.view_picking_form").id, "form")]
            action["res_id"] = pickings.id
        return action

    @api.model
    def create(self, vals):
        vals["name"] = self.env["ir.sequence"].next_by_code("stock.transfer.request")
        return super(StockTransferRequest, self).create(vals)

    def unlink(self):
        if self.filtered(lambda r: r.state != "draft"):
            raise UserError(_("Only requests on draft state can be deleted"))
        return super(StockTransferRequest, self).unlink()


class StockTransferRequestLine(models.Model):
    _name = "stock.transfer.request.line"
    _description = "Stock Transfer Request Line"
    _rec_name = "product_id"

    request_id = fields.Many2one('stock.transfer.request', ondelete='cascade')
    product_id = fields.Many2one('product.product', domain=[('type', '!=', 'service')], required=True)
    product_qty = fields.Float('Approved Quantity')
    product_qty_req_packaging = fields.Float('Approved Quantity')
    company_id = fields.Many2one(related='request_id.company_id')
    move_ids = fields.Many2many('stock.move', string='Reservation', readonly=True, copy=False)

    product_primary_packaging_id = fields.Many2one('product.packaging', string='Primary Packaging', default=False,
                                           domain="[('sales', '=', True), ('product_id','=',product_id)]")

    product_packaging_id = fields.Many2one('product.packaging', string='Packaging', default=False,
                                           domain="[('sales', '=', True), ('product_id','=',product_id)]")
    requested_qty = fields.Float('Requested Quantity')

    requested_qty_primary = fields.Float('Requested Quantity (P)')

    available_stock = fields.Float(string='Stock', default=0.0)
    available_stock_on_primary = fields.Float(string='Stock', default=0.0)

    state = fields.Selection(related="request_id.state")

    available_stock_on_main = fields.Float(compute='_compute_available_stock_on_main', string='Main Stock')

    @api.onchange('product_qty')
    def onchange_approved_qty(self):
        for line in self:
            if line.product_packaging_id:
                line.product_qty_req_packaging = line.product_qty / line.product_packaging_id.qty


    def _compute_available_stock_on_main(self):
        """
        Compute the stock in vansales main location.
        """
        for line in self:
            available_stock_on_main  = 0
            request_id = line.request_id
            lot_ids = self.env['stock.lot'].search([('product_id', '=', line.product_id.id)])
            available_stock = 0
            for lot in lot_ids:
                quants = lot.quant_ids.filtered(lambda q: q.location_id.id == request_id.van_main_location_id.id)
                available_stock += sum(quants.mapped('available_quantity'))
            line.available_stock_on_main = available_stock




    @api.onchange('product_id')
    def onchange_product_id(self):
        if not self.product_id:
            self.product_packaging_id = False
            self.available_stock = 0
            self.requested_qty = 0
        else:
            product_packaging_id = False
            product_primary_packaging_id = False
            for packaging in self.product_id.packaging_ids:
                if packaging.primary_unit:
                    product_packaging_id = packaging.id
                    product_primary_packaging_id = packaging.id


            lot_ids = self.env['stock.lot'].search([('product_id', '=', self.product_id.id)])
            available_stock = 0
            for lot in lot_ids:
                quants = lot.quant_ids.filtered(lambda q: q.location_id.id == self.request_id.location_id.id)
                available_stock += sum(quants.mapped('available_quantity'))
            self.available_stock = available_stock
            self.available_stock_on_primary = available_stock

            self.product_packaging_id = product_packaging_id
            self.product_primary_packaging_id = product_primary_packaging_id

    @api.onchange('product_packaging_id')
    def onchange_product_packaging_id(self):
        if self.available_stock_on_primary > 0 and self.product_packaging_id:
            self.available_stock = self.available_stock_on_primary / self.product_packaging_id.qty

        if self.product_packaging_id:
            self.requested_qty_primary = self.requested_qty * self.product_packaging_id.qty

    @api.onchange('requested_qty')
    def onchange_requested_qty(self):
        if self.product_packaging_id:
            self.requested_qty_primary = self.requested_qty * self.product_packaging_id.qty



    def _prepare_stock_move_vals(self, picking, picking_type_id, location_id, location_dest_id):
        self.ensure_one()
        date_planned = self.request_id.expected_date or fields.Datetime.now()
        request_id = self.request_id
        values = {
            'name': self.product_id.name,
            'product_id': self.product_id.id,
            'date': date_planned,
            'picking_id': picking.id,
            'state': 'draft',
            'company_id': self.company_id.id,
            'picking_type_id': picking_type_id.id,
            'origin': request_id.name,
            'product_uom_qty': self.product_qty,
            'product_uom': self.product_id.uom_id.id,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
        }
        return values

    def _create_stock_moves(self, picking, picking_type_id, location_id, location_dest_id):
        values = []
        for line in self:
            values.append(line._prepare_stock_move_vals(picking, picking_type_id, location_id, location_dest_id))
        return self.env['stock.move'].create(values)
