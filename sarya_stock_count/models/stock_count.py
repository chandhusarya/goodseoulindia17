# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta


class StockCount(models.Model):
    _name = "stock.count"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _description = "Stock Count"
    _order = "id desc"

    name = fields.Char(
        string='Stock Count Reference',
        readonly=True,
        required=True,
        default='new',
        copy=False
    )
    date = fields.Datetime(
        string='Inventory Date',
        readonly=False,
        required=True,
        tracking=True,
        default=fields.Datetime.now,
        help="If the inventory adjustment is not validated, date at which the theoritical quantities have been checked.\n"
             "If the inventory adjustment is validated, date at which the inventory adjustment has been validated."
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        readonly=True,
        default=lambda self: self.env.company
    )
    state = fields.Selection(
        string='Status',
        selection=[
            ('draft', 'Draft'),
            ('cancel', 'Cancelled'),
            ('progress', 'In Progress'),
            ('send_for_approval', 'Send For Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('done', 'Validated')],
        copy=False,
        index=True,
        readonly=True,
        default='draft',
        tracking=True
    )
    pos_config_id = fields.Many2one(
        comodel_name='pos.config',
        string='POS Outlet',
        tracking=True,
    )
    stock_count_config_id = fields.Many2one(
        comodel_name='stock.count.config',
        string='Stock Count Item List'
    )
    location_id = fields.Many2one(
        comodel_name='stock.location',
        string="Location",
        tracking=True,
    )
    brand_ids = fields.Many2many(
        comodel_name='product.manufacturer',
        string='Brand',
        domain=[('is_show_in_stock_count', '=', True)]
    )
    line_ids = fields.One2many(
        comodel_name='stock.count.line',
        inverse_name='stock_count_id',
        string='Inventories',
        readonly=False,
        domain=[('is_counted_qty_entered', '=', True)]
    )
    product_count_line_ids = fields.One2many(
        comodel_name='stock.count.line',
        inverse_name='stock_count_id',
        string='Inventories',
        readonly=False,
        domain=[('is_counted_qty_entered', '=', False)]
    )
    stock_move_ids = fields.One2many(
        comodel_name='stock.move',
        inverse_name='stock_count_id',
        string='Stock Moves'
    )
    is_approve_user = fields.Boolean(
        compute='compute_is_approve_user'
    )
    approved_date = fields.Datetime(
        string='Approved Date',
        readonly=True,
        tracking=True
    )
    approved_by = fields.Many2one(
        comodel_name='hr.employee',
        readonly=True,
        string='Approved By'
    )
    validated_date = fields.Datetime(
        string='Validated Date',
        readonly=True,
        tracking=True
    )

    def compute_is_approve_user(self):
        for rec in self:
            if rec.pos_config_id:
                if rec.pos_config_id.stock_count_approve_manager_ids:
                    if self.env.user.employee_id.id in rec.pos_config_id.stock_count_approve_manager_ids.ids:
                        rec.is_approve_user = True
                    else:
                        rec.is_approve_user = False
                else:
                    rec.is_approve_user = False
            else:
                rec.is_approve_user = False

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if res.name == 'new':
            res.name = self.env['ir.sequence'].next_by_code('stock.count')
        return res

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('You cannot delete a record which is not in draft status'))
        return super(StockCount, self).unlink()

    @api.onchange('pos_config_id')
    def _onchange_pos_config(self):
        if self.pos_config_id:
            picking_type_id = self.pos_config_id.picking_type_id
            self.location_id = picking_type_id and picking_type_id.default_location_src_id and picking_type_id.default_location_src_id.id or False
        else:
            self.location_id = False

    def action_reset_counted_qty(self):
        self.mapped('line_ids').write({'counted_qty': 0})

    def action_set_is_counted_qty_entered(self):
        self.line_ids.filtered(lambda check: not check.is_counted_qty_entered).write({'is_counted_qty_entered': True})

    def action_start(self):
        for inventory in self.filtered(lambda x: x.state not in ('done', 'cancel')):
            vals= {'product_count_line_ids': [(0, 0, line_values) for line_values in inventory._get_stock_count_lines_values()]}
            vals.update({'state': 'progress', 'date': fields.Datetime.now()})
            inventory.write(vals)
        for line in self.product_count_line_ids:
            line.compute_all_quantities()


    def action_validate(self):
        self.check_move_forward()

        StockMove = self.env['stock.move'].with_context(inventory_mode=False)
        StockQuant = self.env['stock.quant']

        for line in self.line_ids:
            product = line.product_id
            location = line.location_id
            company = self.company_id

            inventory_location = product.with_company(
                company
            ).property_stock_inventory

            # ---------------------------------------------------------
            # Fetch ALL quants
            # ---------------------------------------------------------
            quants = StockQuant.search([
                ('product_id', '=', product.id),
                ('location_id', '=', location.id),
                ('company_id', '=', company.id),
            ], order="in_date asc, id asc")

            if not quants:
                main_quant = StockQuant.create({
                    'product_id': product.id,
                    'location_id': location.id,
                    'company_id': company.id,
                })
                quants = main_quant
            else:
                main_quant = quants[:1]

            # ---------------------------------------------------------
            # PHASE 1: QUANT CONSOLIDATION
            # Track its stock impact
            # ---------------------------------------------------------
            consolidation_effect = 0.0

            for quant in quants:
                if quant == main_quant:
                    continue

                if abs(quant.quantity) < 0.000001:
                    continue

                qty = abs(quant.quantity)

                if quant.quantity > 0:
                    # Remove extra positive stock
                    source = location
                    dest = inventory_location
                    consolidation_effect -= qty
                else:
                    # Neutralize negative stock
                    source = inventory_location
                    dest = location
                    consolidation_effect += qty

                mv_vals = quant._get_inventory_move_values(
                    qty,
                    source,
                    dest,
                )

                mv_vals.update({
                    'name': f"Quant Consolidation : %s, product: %s (qty: %s)" % (
                        self.name,
                        product.display_name,
                        abs(qty)
                    ),
                    'stock_count_id': self.id,
                    'origin': self.name,
                })

                move = StockMove.create(mv_vals)
                move._action_done()

            # ---------------------------------------------------------
            # PHASE 2: APPLY ONLY REMAINING DIFFERENCE
            # ---------------------------------------------------------
            initial_diff = line.system_stock_diff_quantity
            remaining_diff = initial_diff - consolidation_effect

            if abs(remaining_diff) >= 0.000001:

                if remaining_diff > 0:
                    source = inventory_location
                    dest = location
                else:
                    source = location
                    dest = inventory_location

                mv_vals = main_quant._get_inventory_move_values(
                    abs(remaining_diff),
                    source,
                    dest,
                )

                mv_vals.update({
                    'name': "Stock Count : %s, product: %s (qty: %s)" % (
                        self.name,
                        product.display_name,
                        abs(remaining_diff)
                    ),
                    'stock_count_id': self.id,
                    'origin': self.name,
                })

                move = StockMove.create(mv_vals)
                move._action_done()

        # ---------------------------------------------------------
        # Finalize
        # ---------------------------------------------------------
        self.write({
            'state': 'done',
            'validated_date': fields.Datetime.now(),
        })

    # def action_validate(self):
    #     # move_vals = []
    #     # for inv_line in self.line_ids:
    #
    #         # print("\n\n\n===================================*******89999")
    #         # print("inv_line.inventory_diff_quantity ==>> ", inv_line.inventory_diff_quantity)
    #         # print("inv_line.quant_id ==>> ", inv_line.quant_id)
    #         # print("inv_line.quant_id.product_uom_id ==>> ", inv_line.quant_id.product_uom_id)
    #         # print("inv_line.quant_id.product_uom_id.rounding ==>> ", inv_line.quant_id.product_uom_id.rounding)
    #         #
    #         # if float_compare(inv_line.stock_diff_quantity, 0, precision_rounding=inv_line.quant_id.product_uom_id.rounding) > 0:
    #         #     valu = inv_line.quant_id._get_inventory_move_values(inv_line.inventory_diff_quantity,
    #         #                                          inv_line.quant_id.product_id.with_company(
    #         #                                              inv_line.quant_id.company_id).property_stock_inventory,
    #         #                                          inv_line.quant_id.location_id, package_dest_id=inv_line.quant_id.package_id)
    #         #     valu['name'] = "Stock Update (Wastage Calculation) " + str(self.name)
    #         #     valu['inventory_id'] = self.id
    #         #     move_vals.append(valu)
    #         # else:
    #         #     valu = inv_line.quant_id._get_inventory_move_values(-inv_line.inventory_diff_quantity,
    #         #                                          inv_line.quant_id.location_id,
    #         #                                          inv_line.quant_id.product_id.with_company(
    #         #                                              inv_line.quant_id.company_id).property_stock_inventory,
    #         #                                          package_id=inv_line.quant_id.package_id)
    #         #     valu['name'] = "Stock Bulk Update " + str(self.name)
    #         #     valu['inventory_id'] = self.id
    #         #     move_vals.append(valu)
    #
    #     # moves = self.env['stock.move'].with_context(inventory_mode=False).create(move_vals)
    #     # moves._action_done()
    #     self.check_move_forward()
    #     for line in self.line_ids:
    #         if line.stock_diff_quantity > 0.000001:
    #             balance_qty = line.stock_diff_quantity
    #             while balance_qty > 0.000001:
    #
    #                 quant = self.env['stock.quant'].search([('location_id', '=', line.location_id.id),
    #                                                         ('quantity', '>', 0.0001),
    #                                                         ('product_id', '=', line.product_id.id)
    #                                                         ], order="in_date asc",
    #                                                        limit=1)
    #
    #                 print("\n\n\nlocation_id ==>> ", line.location_id.name)
    #                 print("product_id  ==>> ", line.product_id.name)
    #                 print("balance_qty ==>> ", balance_qty)
    #                 print("dfffffffffffff ==>> ", quant)
    #
    #                 if not quant:
    #                     msg = "Not enough stock for product: %s. Stock required." % (line.product_id.display_name)
    #                     raise UserError(_(msg))
    #
    #                 qty_to_move = balance_qty
    #                 # if qty_to_move > quant.quantity:
    #                 #     qty_to_move = quant.quantity
    #                 balance_qty = balance_qty - qty_to_move
    #
    #                 mv_vals = quant._get_inventory_move_values(qty_to_move,
    #                                                            quant.product_id.with_company(
    #                                                                quant.company_id).property_stock_inventory,
    #                                                            quant.location_id,
    #                                                            package_id=quant.package_id)
    #                 mv_vals['name'] = "Stock Count : " + str(self.name) + ", product: " + line.product_id.name + "( qty : " + str(qty_to_move) + ")"
    #                 mv_vals['stock_count_id'] = self.id
    #                 mv_vals['origin'] = self.name
    #                 # mv_vals['location_dest_id'] = scrap_location_id.id
    #                 print('cvvvvvvvvvvvvv', mv_vals)
    #                 moves = self.env['stock.move'].with_context(inventory_mode=False).create([mv_vals])
    #                 print('gggggg', moves)
    #
    #                 moves._action_done()
    #         if line.stock_diff_quantity < 0.000001:
    #             balance_qty = abs(line.stock_diff_quantity)
    #             while balance_qty > 0.000001:
    #
    #                 quant = self.env['stock.quant'].search([('location_id', '=', line.location_id.id),
    #                                                         ('quantity', '>', 0.0001),
    #                                                         ('product_id', '=', line.product_id.id)
    #                                                         ], order="in_date asc",
    #                                                        limit=1)
    #
    #                 print("\n\n\nlocation_id ==>> ", line.location_id.name)
    #                 print("product_id  ==>> ", line.product_id.name)
    #                 print("balance_qty ==>> ", balance_qty)
    #                 print("dfffffffffffff ==>> ", quant)
    #
    #                 if not quant:
    #                     msg = "Not enough stock for product: %s. Stock required." % (line.product_id.display_name)
    #                     raise UserError(_(msg))
    #
    #                 qty_to_move = abs(balance_qty)
    #                 if qty_to_move > quant.quantity:
    #                     qty_to_move = quant.quantity
    #                 balance_qty = qty_to_move - abs(balance_qty)
    #
    #                 mv_vals = quant._get_inventory_move_values(qty_to_move,
    #                                                            quant.location_id,
    #                                                            quant.product_id.with_company(
    #                                                                quant.company_id).property_stock_inventory,
    #                                                            package_id=quant.package_id)
    #                 mv_vals['name'] = "Stock Count : " + str(self.name) + ", product: " + line.product_id.name + "( qty : " + str(qty_to_move) + ")"
    #                 mv_vals['stock_count_id'] = self.id
    #                 mv_vals['origin'] = self.name
    #                 # mv_vals['location_dest_id'] = scrap_location_id.id
    #                 print('cvvvvvvvvvvvvv', mv_vals)
    #                 moves = self.env['stock.move'].with_context(inventory_mode=False).create([mv_vals])
    #                 print('gggggg', moves)
    #
    #                 moves._action_done()
    #
    #     self.write({'state': 'done', 'validated_date': fields.Datetime.now()})

    def action_draft(self):
        if self.state != 'done':
            self.write({'product_count_line_ids': [(5,)], 'line_ids': [(5,)], 'state': 'draft'})

    def action_cancel(self):
        if self.state != 'done':
            self.write({'state': 'cancel'})

    def check_move_forward(self):
        now = fields.Datetime.now()

        # Difference between now and saved datetime
        diff = now - self.date

        # Temporary commented
        # if diff > timedelta(hours=24):
        #     raise ValidationError("You cannot proceed. This record is older than 24 hours.")

    def action_send_for_approval(self):
        # Check for empty lines
        if not self.line_ids:
            raise ValidationError(_('Please add at least one line before sending for approval.'))

        # Check configuration
        if not self.pos_config_id.sudo().stock_count_approve_manager_ids:
            raise ValidationError(_('Please configure Stock count approve managers.'))

        # Check move forward
        self.check_move_forward()

        # Check if real qty is entered in all lines
        check_again = self.line_ids.filtered(lambda check: not check.is_counted_qty_entered)
        if check_again:
            raise ValidationError(_('Recheck the real quantity in lines and enable remaining is real qty entered.'))

        # Set state
        self.state = 'send_for_approval'

    def action_approve(self):
        self.check_move_forward()

        self.approved_date = fields.Datetime.now()
        self.state = 'approved'
        self.approved_by = self.env.user.employee_id.id

    def action_reject(self):
        self.check_move_forward()

        self.state = 'rejected'

    def _get_stock_count_lines_values(self):
        vals = []

        if not self.stock_count_config_id:
            raise ValidationError(_('Please choose Stock Count Item List.'))

        # Get all products from all stock count configs (NO duplicates)
        products = self.stock_count_config_id.mapped('allowed_product_ids')

        for product in products:
            vals.append({
                'product_id': product.id,
                'location_id': self.location_id.id,
                'price': product.standard_price,
            })

        return vals
