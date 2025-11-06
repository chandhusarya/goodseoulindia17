from odoo import models, fields, _, api, SUPERUSER_ID
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_round, float_is_zero, groupby
from datetime import date

from datetime import datetime, timedelta,date
import time

from twilio.rest import Client
import json


class InternalStockTransfer(models.Model):
    _name = 'internal.stock.transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Internal Stock Transfer'
    _order = 'name desc, id desc'

    def _default_picking_type_id(self):
        picking_type_code = "internal"
        if picking_type_code:
            picking_types = self.env['stock.picking.type'].search([
                ('code', '=', picking_type_code),
                ('company_id', '=', self.env.company.id),
            ])
            return picking_types[:1].id

    name = fields.Char('Reference', default='/', copy=False, readonly=True)
    location_src_id = fields.Many2one('stock.location', 'From Warehouse', check_company=True)
    transfer_location_id = fields.Many2one('stock.location', 'Transfer Location', check_company=True)
    location_dest_id = fields.Many2one('stock.location', 'To Warehouse', check_company=True)

    scrap_location_id = fields.Many2one('stock.location', 'Scrap Location', check_company=True)

    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda s: s.env.company.id, index=True)
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type',
        required=True, readonly=True, index=True,
        default=_default_picking_type_id)
    move_ids = fields.One2many('stock.move', 'internal_transfer_id', string="Stock Moves", copy=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('product_selection', 'Product Selection'),
        ('waiting_from_wh_confirmation', 'Waiting From WH Confirmation'),
        ('stock_confirmed_from_wh', 'Stock Confirmed From Warehouse'),
        ('in_transit', 'In Transit'),
        ('variation_on_receiving', 'Variation On Receiving'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', copy=False, store=True, tracking=True, default="draft")
    picking_type_code = fields.Char("Picking Type Code", default="internal")
    from_location_transfer = fields.Many2one('stock.picking', 'From Location Transfer')
    to_location_transfer = fields.Many2one('stock.picking', 'To Location Transfer')
    transfer_lines = fields.One2many('internal.stock.transfer.lines', 'transfer_id', string='Lines')

    scrap_transfer = fields.Many2one('stock.picking', 'Scrap Transfer')

    discrepancy_transfer_to_from_wh = fields.Many2one('stock.picking', 'Transfer discrepancy back to from WH')

    discrepancy_transfer_to_to_wh = fields.Many2one('stock.picking', 'Transfer discrepancy back to To WH')

    from_wh_responsible_employee = fields.Many2many('hr.employee', 'from_wh_responsible_employee', 'transfer_id',
                                                'employee_id', string='From WH Responsible')

    to_wh_responsible_employee = fields.Many2many('hr.employee', 'to_wh_responsible_employee', 'transfer_id',
                                           'employee_id', string='To WH Responsible')

    stock_required_on = fields.Date("Stock Required On (Vehicle Availability Date)")

    total_product_weight = fields.Float(string="Total Weight", compute="_compute_total_product_weight")
    total_product_gross_weight = fields.Float(string="Total Weight", compute="_compute_total_product_weight")

    def _compute_total_product_weight(self):
        for transfer in self:
            weight, gross_weight = 0, 0
            for line in transfer.transfer_lines:
                if line.product_id and line.packaging_id:
                    pack_qty = line.packaging_id.qty
                    weight += (line.product_id.weight)*pack_qty*line.stock_transferred
                    gross_weight += (line.product_id.gross_weight)*pack_qty*line.stock_transferred
            transfer.total_product_weight = weight
            transfer.total_product_gross_weight = gross_weight


    def send_notification(self, employee_ids, message, subject):

        for employee_id in employee_ids:
            # Email notification
            mail_content = "Dear " + str(employee_id.name)
            print("message =========>> ", message)
            mail_content += "<br/><br/>" + message
            main_content = {
                "subject": subject,
                "body_html": mail_content,
                "email_to": employee_id.work_email,
            }
            self.env['mail.mail'].sudo().create(main_content).send()

            #Whatsapp message
            account_sid = self.env['ir.config_parameter'].sudo().get_param('twilio.account_sid', False)
            auth_token = self.env['ir.config_parameter'].sudo().get_param('twilio.auth_token', False)
            from_number = self.env['ir.config_parameter'].sudo().get_param('twilio.from', False)
            if employee_id.whatsapp_number:
                to_number = employee_id.whatsapp_number
            else:
                # Fallback to mobile or work phone if whatsapp number is not available
                to_number = employee_id.mobile_phone and employee_id.mobile_phone or employee_id.work_phone

            if account_sid and auth_token and from_number and to_number:
                from_number = "whatsapp:%s" % from_number
                to_number = to_number.replace(" ", '')
                to_number = "whatsapp:%s" % to_number
                button_url = "/#id=" + str(self.id) + "&cids=1&menu_id=710&action=1061&model=internal.stock.transfer&view_type=form"
                content_variables = json.dumps({"1": message,
                                     "2": button_url})
                client = Client(account_sid, auth_token)
                tillow_message = client.messages.create(
                    from_=from_number,
                    content_sid='HX920d72f7157208489eaa073a2a7a82d3',
                    content_variables=content_variables,
                    to=to_number)


    def view_from_wh_stock_transfer(self):
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")
        form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
        if 'views' in action:
            action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
        else:
            action['views'] = form_view
        action['res_id'] = self.from_location_transfer.id
        return action

    def view_to_wh_stock_receiving(self):
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")
        form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
        if 'views' in action:
            action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
        else:
            action['views'] = form_view
        action['res_id'] = self.to_location_transfer.id
        return action

    def process_stock_mismatch(self):

        for transfer in self:

            items_to_scrap = []
            items_to_move_from_wh = []
            items_to_move_to_wh = []

            for line in transfer.transfer_lines:
                if line.stock_missing > 0.0001:
                    for line_detail in line.line_detail:
                        if line_detail.missing_stock > 0.0001:
                           if not line_detail.resolution:
                               raise UserError(_("Please select resolution for missing stock %s" % line.product_id.name))
                           if line_detail.resolution == 'scrap':
                                 items_to_scrap.append({
                                      'product_id': line.product_id.id,
                                      'lot_id': line_detail.lot_id.id,
                                      'quantity': line_detail.missing_stock
                                 })
                           elif line_detail.resolution == 'move_to_from_wh':
                               items_to_move_from_wh.append({
                                      'product_id': line.product_id.id,
                                      'lot_id': line_detail.lot_id.id,
                                      'quantity': line_detail.missing_stock
                                 })
                           elif line_detail.resolution == 'move_to_to_wh':
                                items_to_move_to_wh.append({
                                      'product_id': line.product_id.id,
                                      'lot_id': line_detail.lot_id.id,
                                      'quantity': line_detail.missing_stock
                                 })

            if items_to_scrap:
                self.create_picking_scrap(items_to_scrap)

            if items_to_move_from_wh:
                self.create_picking_move_to_from_wh(items_to_move_from_wh)

            if items_to_move_to_wh:
                self.create_picking_move_to_to_wh(items_to_move_to_wh)

            transfer.state = 'done'

    def create_picking_move_to_to_wh(self, items_to_move_to_wh):
        Picking = self.env['stock.picking']
        Move = self.env['stock.move']
        MoveLine = self.env['stock.move.line']

        picking = Picking.create({
            'picking_type_id': self.env.ref('stock.picking_type_internal').id,  # Internal Transfer Type
            'location_id': self.transfer_location_id.id,
            'location_dest_id': self.location_src_id.id,
            'origin': self.name,
            'internal_transfer_id': self.id,
        })
        self.discrepancy_transfer_to_to_wh = picking.id

        grouped_item = {}
        for item in items_to_move_to_wh:
            product_id_str = str(item['product_id'])
            lot_id = item['lot_id']

            if product_id_str not in grouped_item:
                grouped_item[product_id_str] = []

            # Check if lot already exists for the product
            found = False
            for entry in grouped_item[product_id_str]:
                if entry['lot_id'] == lot_id:
                    entry['quantity'] += item['quantity']
                    found = True
                    break
            if not found:
                grouped_item[product_id_str].append(item.copy())

        for product_id in grouped_item:
            product = self.env['product.product'].browse(int(product_id))
            product_uom_qty = 0
            for item in grouped_item[product_id]:
                product_uom_qty += item['quantity']

            new_move = Move.create({
                'picking_id': picking.id,
                'name': f"{product.name} Scrap Transfer",
                'product_id': product.id,
                'product_uom_qty': product_uom_qty,  # Ensure this matches stock.move.line sum
                'product_uom': product.uom_po_id.id,
                'location_id': self.transfer_location_id.id,
                'location_dest_id': self.location_src_id.id,
                'state': 'draft',  # Ensures proper reservation
            })
            for item in grouped_item[product_id]:
                stock_quant = self.env['stock.quant'].search([
                    ('location_id', '=', self.transfer_location_id.id),
                    ('product_id', '=', product.id),
                    ('lot_id', '=', item['lot_id']),
                    ('quantity', '>=', item['quantity'])])
                MoveLine.create({
                    'move_id': new_move.id,
                    'picking_id': picking.id,
                    'product_id': product.id,
                    'quantity': item['quantity'],
                    'product_uom_id': product.uom_po_id.id,
                    'location_id': self.transfer_location_id.id,
                    'location_dest_id': self.location_src_id.id,
                    'quant_id': stock_quant.id,
                    'lot_id': item['lot_id'],
                })
        picking.action_confirm()
        picking.button_validate()


    def create_picking_move_to_from_wh(self, items_to_move_from_wh):
        Picking = self.env['stock.picking']
        Move = self.env['stock.move']
        MoveLine = self.env['stock.move.line']

        picking = Picking.create({
            'picking_type_id': self.env.ref('stock.picking_type_internal').id,  # Internal Transfer Type
            'location_id': self.transfer_location_id.id,
            'location_dest_id': self.location_src_id.id,
            'origin': self.name,
            'internal_transfer_id': self.id,
        })
        self.discrepancy_transfer_to_from_wh = picking.id

        grouped_item = {}
        for item in items_to_move_from_wh:
            product_id_str = str(item['product_id'])
            lot_id = item['lot_id']

            if product_id_str not in grouped_item:
                grouped_item[product_id_str] = []

            # Check if lot already exists for the product
            found = False
            for entry in grouped_item[product_id_str]:
                if entry['lot_id'] == lot_id:
                    entry['quantity'] += item['quantity']
                    found = True
                    break
            if not found:
                grouped_item[product_id_str].append(item.copy())

        for product_id in grouped_item:
            product = self.env['product.product'].browse(int(product_id))
            product_uom_qty = 0
            for item in grouped_item[product_id]:
                product_uom_qty += item['quantity']

            new_move = Move.create({
                'picking_id': picking.id,
                'name': f"{product.name} Scrap Transfer",
                'product_id': product.id,
                'product_uom_qty': product_uom_qty,  # Ensure this matches stock.move.line sum
                'product_uom': product.uom_po_id.id,
                'location_id': self.transfer_location_id.id,
                'location_dest_id': self.location_src_id.id,
                'state': 'draft',  # Ensures proper reservation
            })
            for item in grouped_item[product_id]:
                stock_quant = self.env['stock.quant'].search([
                    ('location_id', '=', self.transfer_location_id.id),
                    ('product_id', '=', product.id),
                    ('lot_id', '=', item['lot_id']),
                    ('quantity', '>=', item['quantity'])])
                MoveLine.create({
                    'move_id': new_move.id,
                    'picking_id': picking.id,
                    'product_id': product.id,
                    'quantity': item['quantity'],
                    'product_uom_id': product.uom_po_id.id,
                    'location_id': self.transfer_location_id.id,
                    'location_dest_id': self.location_src_id.id,
                    'quant_id': stock_quant.id,
                    'lot_id': item['lot_id'],
                })
        picking.action_confirm()
        picking.button_validate()



    def create_picking_scrap(self, items_to_scrap):
        Picking = self.env['stock.picking']
        Move = self.env['stock.move']
        MoveLine = self.env['stock.move.line']

        picking = Picking.create({
            'picking_type_id': self.env.ref('stock.picking_type_internal').id,  # Internal Transfer Type
            'location_id': self.transfer_location_id.id,
            'location_dest_id': self.scrap_location_id.id,
            'origin': self.name,
            'internal_transfer_id': self.id,
        })
        self.scrap_transfer = picking.id

        grouped_item = {}
        for item in items_to_scrap:
            product_id_str = str(item['product_id'])
            lot_id = item['lot_id']

            if product_id_str not in grouped_item:
                grouped_item[product_id_str] = []

            # Check if lot already exists for the product
            found = False
            for entry in grouped_item[product_id_str]:
                if entry['lot_id'] == lot_id:
                    entry['quantity'] += item['quantity']
                    found = True
                    break
            if not found:
                grouped_item[product_id_str].append(item.copy())

        for product_id in grouped_item:
            product = self.env['product.product'].browse(int(product_id))
            product_uom_qty = 0
            for item in grouped_item[product_id]:
                product_uom_qty += item['quantity']

            new_move = Move.create({
                'picking_id': picking.id,
                'name': f"{product.name} Scrap Transfer",
                'product_id': product.id,
                'product_uom_qty': product_uom_qty,  # Ensure this matches stock.move.line sum
                'product_uom': product.uom_po_id.id,
                'location_id': self.transfer_location_id.id,
                'location_dest_id': self.scrap_location_id.id,
                'state': 'draft',  # Ensures proper reservation
            })
            for item in grouped_item[product_id]:
                stock_quant = self.env['stock.quant'].search([
                    ('location_id', '=', self.transfer_location_id.id),
                    ('product_id', '=', product.id),
                    ('lot_id', '=', item['lot_id']),
                    ('quantity', '>=', item['quantity'])])
                MoveLine.create({
                    'move_id': new_move.id,
                    'picking_id': picking.id,
                    'product_id': product.id,
                    'quantity': item['quantity'],
                    'product_uom_id': product.uom_po_id.id,
                    'location_id': self.transfer_location_id.id,
                    'location_dest_id': self.scrap_location_id.id,
                    'quant_id': stock_quant.id,
                    'lot_id': item['lot_id'],
                })
        picking.action_confirm()
        picking.button_validate()



    def select_products(self):
        self.state = 'product_selection'


    @api.model_create_multi
    def create(self, vals_list):
        scheduled_dates = []
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('internal.stock.transfer')
        pickings = super().create(vals_list)
        return pickings

    def action_request(self):
        for transfer in self:
            transfer.state = 'waiting_from_wh_confirmation'
            Picking = self.env['stock.picking']
            Move = self.env['stock.move']

            picking = Picking.create({
                'picking_type_id': self.env['stock.picking.type'].search([('code', '=', 'internal')], limit=1).id,#.ref('stock.picking_type_internal').id,  # Internal Transfer Type
                'location_id': self.location_src_id.id,
                'location_dest_id': self.transfer_location_id.id,
                'origin': self.name,
                'transfer_from_wh_id': transfer.id,
            })
            self.from_location_transfer = picking.id

            for line in transfer.transfer_lines:
                move = Move.create({
                    'picking_id': picking.id,
                    'name': f"{line.product_id.name} Transfer",
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.packaging_qty * line.packaging_id.qty,  # Ensure this matches stock.move.line sum
                    'product_uom': line.product_id.uom_po_id.id,
                    'location_id': transfer.location_src_id.id,
                    'location_dest_id': transfer.transfer_location_id.id,
                    'state': 'draft',  # Ensures proper reservation
                })


            transfer.send_notification(transfer.from_wh_responsible_employee,
                                       "Request Number: %s, From Location: %s , To Location: %s. Please arrange requested stock needs to be shipped on %s" % (transfer.name,
                                        transfer.location_src_id.name, transfer.location_dest_id.name,
                                        transfer.stock_required_on and str(transfer.stock_required_on) or 'NA'),
                                       "Stock Transfer Request")


    def do_stock_tranfer_transit_to_to_wh(self):

        for transfer in self:
            from_location_transfer = transfer.from_location_transfer
            Picking = self.env['stock.picking']
            Move = self.env['stock.move']
            MoveLine = self.env['stock.move.line']

            picking = Picking.create({
                'picking_type_id': self.env.ref('stock.picking_type_internal').id,  # Internal Transfer Type
                'location_id': transfer.transfer_location_id.id,
                'location_dest_id': transfer.location_dest_id.id,
                'origin': self.name,
                'transfer_to_wh_id': transfer.id,
            })
            transfer.to_location_transfer = picking.id
            for move in from_location_transfer.move_ids:
                new_move = Move.create({
                    'picking_id': picking.id,
                    'name': f"{move.product_id.name} Transfer",
                    'product_id': move.product_id.id,
                    'product_uom_qty': move.product_uom_qty,  # Ensure this matches stock.move.line sum
                    'product_uom': move.product_uom.id,
                    'location_id': transfer.transfer_location_id.id,
                    'location_dest_id': transfer.location_dest_id.id,
                    'state': 'draft',  # Ensures proper reservation
                })
                for move_line in move.move_line_ids:
                    stock_quant = self.env['stock.quant'].search([
                                        ('location_id', '=', transfer.transfer_location_id.id),
                                        ('product_id', '=', move_line.product_id.id),
                                        ('lot_id', '=', move_line.lot_id.id)])
                    MoveLine.create({
                        'move_id': new_move.id,
                        'picking_id': picking.id,
                        'product_id': move_line.product_id.id,
                        'quantity': move_line.quantity,
                        'product_uom_id': move_line.product_uom_id.id,
                        'location_id': transfer.transfer_location_id.id,
                        'location_dest_id': transfer.location_dest_id.id,
                        'quant_id': stock_quant.id,
                        'lot_id': move_line.lot_id.id,
                    })

            transfer.send_notification(transfer.to_wh_responsible_employee,
                                       "Request Number: %s, From Location: %s , To Location: %s, Please process GRN upon arrival of Goods" % (
                                       transfer.name, transfer.location_src_id.name, transfer.location_dest_id.name),
                                       "Stock Transfer GRN")

    def update_line_details(self):
        for line in self.transfer_lines:
            line.line_detail.unlink()
        if self.from_location_transfer:
            self.update_transfered_stock_on_details()
        if self.to_location_transfer and self.to_location_transfer.state == 'done':
            self.update_grn_stock_on_details()

    def update_grn_stock_on_details(self):
        for move in self.to_location_transfer.move_ids:

            for move_line in move.move_line_ids:
                for line in self.transfer_lines:
                    if line.product_id.id == move.product_id.id:
                        is_stock_updated = False
                        for detail in line.line_detail:
                            if detail.lot_id.id == move_line.lot_id.id:
                                detail.stock_received += move_line.quantity
                                is_stock_updated = True

                        if not is_stock_updated:
                            self.env['internal.stock.transfer.details'].create({
                                'transfer_line_id': line.id,
                                'lot_id': move_line.lot_id.id,
                                'stock_received': move_line.quantity,
                            })



    def update_transfered_stock_on_details(self):
        for move in self.from_location_transfer.move_ids:
            for move_line in move.move_line_ids:
                for line in self.transfer_lines:
                    if line.product_id.id == move.product_id.id:

                        is_stock_updated = False
                        for detail in line.line_detail:
                            if detail.lot_id.id == move_line.lot_id.id:
                                detail.stock_transferred += move_line.quantity
                                is_stock_updated = True

                        if not is_stock_updated:
                            self.env['internal.stock.transfer.details'].create({
                                'transfer_line_id': line.id,
                                'lot_id': move_line.lot_id.id,
                                'stock_transferred': move_line.quantity,
                                'stock_received': 0.0
                            })


class StockMove(models.Model):
    _inherit = "stock.move"

    internal_transfer_id = fields.Many2one('internal.stock.transfer', 'Internal Stock Transfer', index=True, check_company=True)


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'



class InternalStockTransferLines(models.Model):
    _name = 'internal.stock.transfer.lines'

    transfer_id = fields.Many2one('internal.stock.transfer', 'Transfer')

    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_uom_qty = fields.Float(string='UOM Quantity', required=True)
    packaging_id = fields.Many2one(comodel_name='product.packaging', string='Packaging',
                                   domain="[('product_id', '=', product_id)]", required=True)
    packaging_qty = fields.Float(string='Quantity', required=True)

    stock_transferred = fields.Float(string='From WH Qty', compute='_compute_stock_transfered')

    stock_received = fields.Float(string='To WH GRN Qty', compute='_compute_stock_received')

    stock_missing = fields.Float(string='Transit Missing Qty', compute='_compute_stock_missing')

    balance_stock_expected = fields.Date(string='Balance Stock Expected Date')

    line_detail = fields.One2many('internal.stock.transfer.details', 'transfer_line_id', string='Line Details')

    can_edit_balance_stock_expected = fields.Boolean(string='Can Edit Balance Stock Expected', compute='_compute_can_edit_bal_expected_date')

    def _compute_can_edit_bal_expected_date(self):
        for line in self:
            if line.transfer_id.state == 'waiting_from_wh_confirmation':
                line.can_edit_balance_stock_expected = True
            else:
                line.can_edit_balance_stock_expected = False


    def action_view_details(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock Transfer Line',
            'view_mode': 'form',
            'res_model': 'internal.stock.transfer.lines',
            'res_id': self.id,
            'views': [(self.env.ref('kg_sarya_inventory.view_internal_stock_transfer_lines_form').id, 'form')],
            'target': 'new',  # or 'current' if you don't want a popup
        }


    def _compute_stock_missing(self):
        for line in self:
            if line.transfer_id.state not in ['draft', 'product_selection', 'waiting_from_wh_confirmation']:
                line.stock_missing = line.stock_transferred - line.stock_received
            else:
                line.stock_missing = 0.0


    @api.onchange('packaging_qty', 'packaging_id')
    def _onchange_packaging_qty(self):
        for line in self:

            if line.packaging_id:
                line.product_uom_qty = line.packaging_qty * line.packaging_id.qty
            else:
                line.product_uom_qty = 0.0
                line.packaging_qty = 0


    def _compute_stock_transfered(self):
        for line in self:
            if line.transfer_id.from_location_transfer:
                move_lines = self.env['stock.move.line'].search([
                    ('product_id', '=', line.product_id.id),
                    ('move_id.picking_id', '=', line.transfer_id.from_location_transfer.id)
                ])
                line.stock_transferred = sum(move_lines.mapped('quantity'))
            else:
                line.stock_transferred = 0.0

    def _compute_stock_received(self):
        for line in self:
            if line.transfer_id.to_location_transfer and line.transfer_id.to_location_transfer.state == 'done':
                move_lines = self.env['stock.move.line'].search([
                    ('product_id', '=', line.product_id.id),
                    ('move_id.picking_id', '=', line.transfer_id.to_location_transfer.id)
                ])
                line.stock_received = sum(move_lines.mapped('quantity'))
            else:
                line.stock_received = 0.0


class InternalStockTransferDetails(models.Model):
    _name = 'internal.stock.transfer.details'

    transfer_line_id = fields.Many2one('internal.stock.transfer.lines', 'Transfer Line')
    lot_id = fields.Many2one('stock.lot', 'Lot Number')
    expiration_date = fields.Datetime('Expiration Date', related='lot_id.expiration_date')
    stock_transferred = fields.Float(string='From WH Qty')
    stock_received = fields.Float(string='To WH GRN Qty')
    missing_stock = fields.Float(string='Transit Missing Qty', compute='_compute_missing_stock')
    resolution = fields.Selection([
        ('scrap', 'Scrap Missing Stock'),
        ('move_to_from_wh', 'Move missing stock to From WH'),
        ('move_to_to_wh', 'Move missing stock to To WH'),
    ], string='Resolution')
    can_edit_resolution = fields.Boolean(string='Can Edit Resolution', compute='_compute_can_edit_resolution')

    def _compute_can_edit_resolution(self):
        for detail in self:
            if detail.transfer_line_id.transfer_id.state == 'variation_on_receiving':
                detail.can_edit_resolution = True
            else:
                detail.can_edit_resolution = False


    def _compute_missing_stock(self):
        for detail in self:
            detail.missing_stock = detail.stock_transferred - detail.stock_received





class StockPicking(models.Model):
    _inherit = 'stock.picking'

    transfer_from_wh_id = fields.Many2one('internal.stock.transfer', 'Internal Transfer from WH')
    transfer_to_wh_id = fields.Many2one('internal.stock.transfer', 'Internal Transfer To WH')

    internal_transfer_id = fields.Many2one('internal.stock.transfer', 'Internal Transfer')


    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        for picking in self:
            if picking.transfer_from_wh_id:
                picking.transfer_from_wh_id.state = 'in_transit'
                picking.transfer_from_wh_id.do_stock_tranfer_transit_to_to_wh()
                picking.transfer_from_wh_id.update_line_details()

                short_delivery_items = []
                for line in picking.transfer_from_wh_id.transfer_lines:
                    if line.product_uom_qty > line.stock_transferred and not line.balance_stock_expected:
                        short_delivery_items.append(line.product_id.name)

                if short_delivery_items:
                    short_delivery_items_str = ', '.join(short_delivery_items)
                    message = "Please update expected balance stock available date for Short delivery items: %s" % short_delivery_items_str
                    raise UserError(message)





            if picking.transfer_to_wh_id:

                is_any_stock_missing = False
                for line in picking.transfer_to_wh_id.transfer_lines:
                    if line.stock_missing > 0.0001:
                        is_any_stock_missing = True
                        break
                if is_any_stock_missing:
                    picking.transfer_to_wh_id.state = 'variation_on_receiving'

                    transfer_to_wh_id = picking.transfer_to_wh_id

                    # Send notification to the responsible employees
                    users = self.env.ref('kg_sarya_inventory.stock_internal_transfer_responsible').users
                    employee_ids = []
                    for user in users:
                        employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
                        employee_ids.append(employee.id)
                    if employee_ids:
                        employees = self.env['hr.employee'].browse(employee_ids)

                        transfer_to_wh_id.send_notification(employees,
                                                   "Variation on GRN. Request Number: %s, From Location: %s , To Location: %s" % (
                                                       transfer_to_wh_id.name, transfer_to_wh_id.location_src_id.name,
                                                       transfer_to_wh_id.location_dest_id.name),
                                                   "Stock Transfer Variation on GRN")

                else:
                    picking.transfer_to_wh_id.state = 'done'

                    users = self.env.ref('kg_sarya_inventory.stock_internal_transfer_responsible').users
                    employee_ids = []
                    for user in users:
                        employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
                        employee_ids.append(employee.id)
                    if employee_ids:
                        employees = self.env['hr.employee'].browse(employee_ids)

                        picking.transfer_to_wh_id.send_notification(employees,
                                                            "Transfer Completed. Request Number: %s, From Location: %s , To Location: %s" % (
                                                                picking.transfer_to_wh_id.name,
                                                                picking.transfer_to_wh_id.location_src_id.name,
                                                                picking.transfer_to_wh_id.location_dest_id.name),
                                                            "Stock Transfer Completed")


                picking.transfer_to_wh_id.update_line_details()
        return res









