from odoo import fields, models, api, _
from odoo.tools import float_utils, float_compare
from odoo.exceptions import UserError



class OutletTransfer(models.Model):
    _name = 'outlet.transfer'
    _description = "Outlet Transfer"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name')
    from_outlet = fields.Many2one(
        'pos.config', string='From Outlet'
    )
    to_outlet = fields.Many2one(
        'pos.config', string='To Outlet'
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        default = lambda self: self.env.company
    )
    comment = fields.Char(
        string='Comment'
    )
    date = fields.Datetime(
        string='Date',
        default=fields.Datetime.now
    )
    state = fields.Selection(string='Status', selection=[
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('sent_for_approval', 'Sent for Approval'),
        ('done', 'Validated')], copy=False, index=True, readonly=True, default='draft', tracking=True)
    outlet_transfer_lines = fields.One2many(
        'outlet.transfer.line', 'outlet_transfer_id',
        string='Outlet transfer Lines'
    )
    picking_ids = fields.One2many(
        'stock.picking',
        'outlet_transfer_id',
        string='Transfers'
    )
    is_approve_user = fields.Boolean(
        compute='compute_is_approve_user'
    )

    @api.depends('state')
    def compute_is_approve_user(self):
        for rec in self:
            is_approve = False
            config_id = rec.env['pos.config'].search([('terminal_type', '=', 'primary')], limit=1)
            if config_id and config_id.advanced_employee_ids and \
                self.env.user.employee_id in config_id.advanced_employee_ids:
                is_approve =  True
            rec.is_approve_user = is_approve

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res.name = self.env['ir.sequence'].next_by_code('outlet.transfer')
        return res

    def send_notification(self, employee_ids, message, subject, button_url):
        for employee_id in employee_ids:
            # Email notification
            main_content = {
                "subject": subject,
                "body_html": message,
                "email_to": employee_id.work_email,
            }
            self.env['mail.mail'].sudo().create(main_content).send()

    def send_for_approval(self):
        if not self.outlet_transfer_lines:
            raise UserError(_("Please add the Inventory Details"))
        self.state = 'sent_for_approval'
        users = self.from_outlet.advanced_employee_ids
        for employee in users:
            subject = 'Outlet Transfer order %s Approval Request' % self.name
            message = 'Hi %s, <br/><br/>Outlet Transfer order %s waiting for Manager approval.' % (employee.name, self.name)
            button_url = "#id=%s&cids=2&menu_id=697&action=876&model=office.purchase&view_type=form" % (
                str(self.id))
            self.send_notification(users, message, subject, button_url)

    def get_action_view_picking(self):
        '''
        This function returns an action that display existing internal orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one internal order to show.
        '''
        pickings = self.picking_ids
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")

        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = pickings.id
        return action

    def action_validate(self):
        for line in self.outlet_transfer_lines:
            if float_compare(line.quantity, 0, precision_rounding=line.product_id.uom_id.rounding) <= 0:
                raise UserError(_("You cannot enter Quantity in zero or negative"))
            if not line.lot_id:
                raise UserError(_("Please enter the lot"))
        picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'internal'),('company_id', '=', self.company_id.id)])
        from_outlet = self.from_outlet.lpo_picking_type_id.default_location_dest_id
        to_outlet = self.to_outlet.lpo_picking_type_id.default_location_dest_id
        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type_id.id,  # Internal Transfer Type
            'location_id': from_outlet.id,
            'location_dest_id': to_outlet.id,
            'origin': self.name,
            'outlet_transfer_id': self.id,
        })
        for line in self.outlet_transfer_lines:
            self.env['stock.move'].create({
                'picking_id': picking.id,
                'name': "Outlet Transfer: " + str(self.name),
                'product_id': line.product_id.id,
                'product_uom_qty': line.primary_quantity,
                'product_uom': line.product_uom.id,
                'location_id': from_outlet.id,
                'location_dest_id': to_outlet.id,
                'state': 'draft',
                'move_line_ids': [(0, 0, {
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_uom.id,
                    'quantity': line.primary_quantity,
                    'location_id': from_outlet.id,
                    'location_dest_id': to_outlet.id,
                    'company_id': self.company_id.id or self.env.company.id,
                    'lot_id': line.lot_id.id,
                })]
            })

        picking.action_confirm()
        picking.button_validate()
        self.write({'state': 'done', 'date': fields.Datetime.now()})

    @api.constrains('from_outlet', 'to_outlet')
    def _check_unique_nonzero_ref(self):
        for record in self:
            if record.from_outlet and record.to_outlet:
                if record.from_outlet == record.to_outlet:
                    raise UserError("From Outlet and To Outlet cannot be same")

class OutletTransferLines(models.Model):
    _name = 'outlet.transfer.line'

    outlet_transfer_id = fields.Many2one(
        'outlet.transfer',
        string='Outlet Transfer'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product'
    )
    primary_unit = fields.Many2one(
        'product.packaging', compute='_find_primary_package',
        string='Primary Unit'
    )
    product_uom = fields.Many2one(
        'uom.uom', related='product_id.uom_id',
        string='Unit'
    )
    quantity = fields.Float(
        string='Quantity'
    )
    packaging = fields.Many2one(
        'product.packaging',
        string='Packaging'
    )
    primary_quantity = fields.Float(
        string='Primary Quantity'
    )
    lot_id = fields.Many2one(
        'stock.lot',
        string='lots / serial numbers'
    )
    available_quantity = fields.Float(
        # related='lot_id.product_qty',
        compute='_compute_available_lots',
        string='Available Quantity'
    )


    def _find_primary_package(self):
        for move in self:
            primary_packaging_id = False
            for pack in move.product_id.packaging_ids:
                if pack.primary_unit:
                    primary_packaging_id = pack.id
            move.primary_unit = primary_packaging_id

    @api.onchange('packaging', 'quantity')
    def onchange_packaging_set_primary_quantitiy(self):
        for move in self:
            if move.packaging and move.quantity:
                move.primary_quantity = move.packaging.qty * move.quantity
            if move.lot_id and move.quantity and move.primary_quantity > move.lot_id.product_qty:
                raise UserError(_("Quantity cannot be greater than that of available in the lot"))

    available_lot_ids = fields.Many2many('stock.lot', compute='_compute_available_lots')

    @api.depends('product_id', 'outlet_transfer_id.from_outlet')
    def _compute_available_lots(self):
        for rec in self:
            from_outlet = rec.outlet_transfer_id.from_outlet.lpo_picking_type_id.default_location_dest_id
            lots = self.env['stock.quant'].search([
                ('product_id', '=', rec.product_id.id),
                ('location_id', '=', from_outlet.id),
                ('quantity', '>', 0),
                ('lot_id', '!=', False),
            ])
            rec.available_lot_ids = lots.mapped('lot_id')
            if rec.lot_id:
                quant = self.env['stock.quant'].search([
                    ('product_id', '=', rec.product_id.id),
                    ('location_id', '=', from_outlet.id),
                    ('quantity', '>', 0),
                    ('lot_id', '=', rec.lot_id.id),
                ])
                rec.available_quantity = quant.available_quantity
            else:
                rec.available_quantity = 0.0




