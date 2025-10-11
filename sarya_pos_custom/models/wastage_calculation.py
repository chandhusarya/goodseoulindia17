from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_utils, float_compare


class POSWastage(models.Model):
    _name = "pos.wastage"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "POS Wastage Calculation"
    _order = "id desc"

    name = fields.Char(string='Inventory Reference', readonly=True, required=True, default='new', copy=False)
    date = fields.Datetime(string='Inventory Date', readonly=True, required=True, default=fields.Datetime.now)
    date_validated = fields.Datetime(string='Validated Date', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    state = fields.Selection(string='Status', selection=[
        ('draft', 'Draft'),
        ('progress', 'In Progress'),
        ('done', 'Validated'),
        ('cancel', 'Cancelled')], copy=False, index=True, readonly=True, default='draft', tracking=True)
    location_id = fields.Many2one('stock.location', "Location")
    category_id = fields.Many2one('product.category', string="Product Category", help="Specify Product Category to focus your inventory on a particular Category.")

    line_ids = fields.One2many('pos.wastage.line', 'wastage_id', string='Inventories', copy=True, readonly=False,)

    filter = fields.Selection(string='Inventory of', selection=[
                              ('none', _('Raw Material Wastage')),
                              ('partial', _('Finished/Intermediate Product Wastage'))],
                              required=True, default='partial', tracking=True)

    exhausted = fields.Boolean('Include Exhausted Products', readonly=True,)
    line_count = fields.Integer('Line Count', compute="compute_line_count", store=True)
    stock_move_ids = fields.One2many('stock.move', 'wastage_id', string='Stock Moves')

    comment = fields.Char("Comment")
    order_type = fields.Selection(string='Type', selection=[
                              ('wastage', _('Wastage')),
                              ('sampling', _('Sampling'))],
                              required=True, default='wastage')
    pos_config_id = fields.Many2one(
        comodel_name='pos.config',
        string='POS Outlet')

    @api.onchange('pos_config_id')
    def _onchange_pos_config(self):
        if self.pos_config_id:
            picking_type_id = self.pos_config_id.picking_type_id
            self.location_id = picking_type_id and picking_type_id.default_location_src_id and picking_type_id.default_location_src_id.id or False
        else:
            self.location_id = False

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res.name = self.env['ir.sequence'].next_by_code('pos.wastage')
        return res

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('You cannot delete a record which is not in draft status'))
        return super(POSWastage, self).unlink()

    @api.depends('state')
    def compute_line_count(self):
        stock_quant = self.env['stock.quant']
        for rec in self:
            rec.line_count = stock_quant.search_count([('stock_inventory_id', '=', rec.id)])

    # def _default_location_id(self):
    #     company_id = self.env.context.get('default_company_id') or self.env.company.id
    #     warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_id)], limit=1)
    #     if warehouse:
    #         return warehouse.lot_stock_id.id
    #     else:
    #         return None

    def action_start(self):
        for inventory in self.filtered(lambda x: x.state not in ('done', 'cancel')):
            vals = {'state': 'progress', 'date': fields.Datetime.now()}
            if (inventory.filter != 'partial') and not inventory.line_ids:
                vals.update(
                    {'line_ids': [(0, 0, line_values) for line_values in inventory._get_inventory_lines_values()]})
            inventory.write(vals)

    # def _get_inventory_lines_values(self):
    #     # TDE CLEANME: is sql really necessary ? I don't think so
    #     locations = self.env['stock.location'].search([('id', 'in', [self._default_location_id()])])
    #     if self.location_id:
    #         locations = self.env['stock.location'].search([('id', 'child_of', [self.location_id.id])])
    #
    #     domain = ' location_id in %s AND quantity != 0 AND active = TRUE'
    #     args = (tuple(locations.ids),)
    #
    #     vals = []
    #     Product = self.env['product.product'].sudo()
    #     # Empty recordset of products available in stock_quants
    #     quant_products = self.env['product.product']
    #     # Empty recordset of products to filter
    #     products_to_filter = self.env['product.product']
    #
    #     # case 0: Filter on company
    #     if self.company_id:
    #         domain += ' AND company_id = %s'
    #         args += (self.company_id.id,)
    #
    #
    #     # case 5: Filter on One product category + Exahausted Products
    #     if self.category_id:
    #         categ_products = Product.search([('categ_id', 'child_of', self.category_id.id)])
    #         domain += ' AND product_id = ANY (%s)'
    #         args += (categ_products.ids,)
    #         products_to_filter |= categ_products
    #
    #     self.env.cr.execute("""SELECT sq.id as quant_id, sq.product_id, sq.location_id, sq.lot_id as prod_lot_id, sq.package_id
    #         FROM stock_quant sq
    #         LEFT JOIN product_product
    #         ON product_product.id = sq.product_id
    #         WHERE %s
    #         GROUP BY quant_id, product_id, location_id, lot_id, package_id """ % domain, args)
    #
    #     for product_data in self.env.cr.dictfetchall():
    #
    #         print("\n\n\n\n")
    #         print("product_data ==>> ", product_data)
    #         quant = self.env['stock.quant'].search([('id', '=', product_data['quant_id'])])
    #         print("quant     =====>> ", quant)
    #
    #         product_id = quant.product_id
    #
    #         packaging_id = False
    #         for pkg in product_id.packaging_ids:
    #             if pkg.primary_unit:
    #                 packaging_id = pkg.id
    #
    #         if not packaging_id:
    #             msg = "For product %s primary stock keeping unit is missing" % product_id.name
    #             raise UserError(_(msg))
    #
    #         product_data['packaging_id'] = packaging_id
    #         product_data['current_stock'] = quant.quantity
    #         product_data['quant_id'] = quant.id
    #         print("\n\n\n\n")
    #         #ooooooooooooooooooooooo
    #         vals.append(product_data)
    #
    #     return vals


    # def old_action_validate(self):
    #     move_vals = []
    #     for inv_line in self.line_ids:
    #         # Check for positive qty
    #         if float_compare(inv_line.adj_qty, 0, precision_rounding=inv_line.product_id.uom_id.rounding) > 0:
    #
    #             if not inv_line.packaging_id:
    #                 msg = "Please select packaging for item %s" % (inv_line.product_id.name)
    #                 raise UserError(_(msg))
    #
    #             wastage_qty = inv_line.packaging_id.qty * inv_line.adj_qty
    #
    #
    #             #Check selected item is final products or raw material
    #             mrp_bom = self.env['mrp.bom'].search([('product_id', '=', inv_line.product_id.id)])
    #             if mrp_bom:
    #                 #This is final product, Reduce stock of the raw materials based on FIFO
    #                 self.process_wastage_with_bom(mrp_bom, wastage_qty)
    #             else:
    #                 if not inv_line.quant_id:
    #                     msg = "Please select expiry date for item %s" % (inv_line.quant_id.product_id.name)
    #                     raise UserError(_(msg))
    #                 valu = inv_line.quant_id._get_inventory_move_values(wastage_qty,
    #                                                      inv_line.quant_id.location_id,
    #                                                      inv_line.quant_id.product_id.with_company(
    #                                                          inv_line.quant_id.company_id).property_stock_inventory,
    #                                                      package_id=inv_line.quant_id.package_id)
    #                 valu['name'] = "Wastage Entry: " + str(self.name)
    #                 valu['wastage_id'] = self.id
    #                 moves = self.env['stock.move'].with_context(inventory_mode=False).create([valu])
    #                 moves._action_done()
    #         else:
    #             raise UserError(_("You cannot enter qty in zero or negative"))
    #
    #     self.write({'state': 'done', 'date_validated': fields.Datetime.now()})

    def action_validate(self):
        Scrap = self.env["stock.scrap"].sudo()
        Quant = self.env["stock.quant"].sudo()
        move_vals = []
        for inv_line in self.line_ids:
            if float_compare(inv_line.adj_qty, 0, precision_rounding=inv_line.product_id.uom_id.rounding) > 0:

                if not inv_line.packaging_id:
                    msg = "Please select packaging for item %s" % (inv_line.product_id.name)
                    raise UserError(_(msg))
                wastage_qty = inv_line.packaging_id.qty * inv_line.adj_qty
                # Check selected item is final products or raw material
                mrp_bom = self.env['mrp.bom'].search([('product_id', '=', inv_line.product_id.id)])
                if mrp_bom:
                    # This is final product, Reduce stock of the raw materials based on FIFO
                    self.process_wastage_with_bom(mrp_bom, wastage_qty)
                else:
                    quants = Quant.search([
                        ("product_id", "=", inv_line.product_id.id),
                        ("location_id", "=", self.location_id.id),
                        ("quantity", ">", 0),
                    ], order="in_date asc")
                    qty_to_scrap = wastage_qty

                    for quant in quants:
                        if qty_to_scrap <= 0:
                            break

                        scrap_qty = min(qty_to_scrap, quant.quantity)
                        print('scrap_qty', scrap_qty)
                        # rsdr
                        scrap_id = Scrap.create({
                            "product_id": inv_line.product_id.id,
                            "scrap_qty": scrap_qty,
                            "company_id": self.env.company.id,
                            "location_id": quant.location_id.id,
                            "lot_id": quant.lot_id.id if quant.lot_id else False,
                            'name': "Wastage Entry: " + str(self.name)
                        })
                        print('scrap_id', scrap_id)
                        scrap_id.action_validate()

                        qty_to_scrap -= scrap_qty
                        for move_line in scrap_id.move_ids:
                            move_line.write({'wastage_id': self.id})

                    if qty_to_scrap > 0:
                        raise UserError(_("Not enough stock to scrap %s for product %s") %
                                        (inv_line.adj_qty, inv_line.product_id.display_name))
            else:
                raise UserError(_("You cannot enter qty in zero or negative"))

        self.write({'state': 'done', 'date_validated': fields.Datetime.now()})

    def process_wastage_with_bom(self, mrp_bom, qty):
        scrap_location_id = self.env['stock.location'].search([('usage', '=', 'inventory'), ('scrap_location', '=', True), ('company_id', '=', self.env.company.id)], limit=1)
        print("\n\n\nscrap_location_id ==>> ", scrap_location_id.name)
        for bom_line in mrp_bom.bom_line_ids:

            total_qty_required = qty * (bom_line.product_qty/mrp_bom.product_qty)


            #Check does it have sub recpie
            sub_mrp_bom = self.env['mrp.bom'].search([('product_id', '=', bom_line.product_id.id)])
            if sub_mrp_bom:
                self.process_wastage_with_bom(sub_mrp_bom, total_qty_required)

            else:
                balance_qty = total_qty_required
                while balance_qty > 0.000001:

                    quant = self.env['stock.quant'].search([('location_id', '=', self.location_id.id),
                                                            ('quantity', '>', 0.0001),
                                                            ('product_id', '=', bom_line.product_id.id)
                                                            ], order="in_date asc",
                                                           limit=1)

                    print("\n\n\nlocation_id ==>> ", self.location_id.name)
                    print("product_id  ==>> ", bom_line.product_id.name)
                    print("total_qty_required ==>> ", total_qty_required)
                    print("balance_qty ==>> ", balance_qty)

                    if not quant:
                        msg = "Not enough stock for raw material: %s of final product: %s. Stock required: %s" % (
                        bom_line.product_id.name,
                        mrp_bom.product_id.name, str(total_qty_required))
                        raise UserError(_(msg))

                    qty_to_move = balance_qty
                    if qty_to_move > quant.quantity:
                        qty_to_move = quant.quantity
                    balance_qty = balance_qty - qty_to_move

                    mv_vals = quant._get_inventory_move_values(qty_to_move,
                                                               quant.location_id,
                                                               quant.product_id.with_company(
                                                                   quant.company_id).property_stock_inventory,
                                                               package_id=quant.package_id)
                    mv_vals['name'] = "Wastage Entry: " + str(self.name) + " Final product: " + mrp_bom.product_id.name \
                                      + "(" + str(qty) + ")"
                    mv_vals['wastage_id'] = self.id
                    mv_vals['location_dest_id'] = scrap_location_id.id
                    moves = self.env['stock.move'].with_context(inventory_mode=False).create([mv_vals])
                    moves._action_done()





    def action_reset_product_qty(self):
        self.mapped('line_ids').write({'product_qty': 0})

    def action_reset_to_draft(self):
        if self.state != 'done':
            self.write({'line_ids': [(5,)], 'state': 'draft'})

    def action_cancel(self):
        if self.state != 'done':
            self.write({'state': 'cancel'})



class POSWastageLine(models.Model):
    _name = "pos.wastage.line"
    _description = "POS Wastage Line"
    _order = "product_id, wastage_id, location_id"

    wastage_id = fields.Many2one('pos.wastage', 'Inventory', index=True, ondelete='cascade')

    product_id = fields.Many2one('product.product', 'Product', domain=[('type', '=', 'product')], required=True)

    packaging_id = fields.Many2one(comodel_name='product.packaging', string='Packaging',
                                   domain="[('product_id', '=', product_id)]")

    location_id = fields.Many2one('stock.location', 'Location', index=True)

    location_dest_id = fields.Many2one('stock.location', 'Location', index=True)

    package_id = fields.Many2one('stock.quant.package', 'Pack', index=True)

    '''
    ****************************************************************
    ************************FIELDS NOT USING************************
    ****************************************************************
    '''
    prod_lot_id = fields.Many2one('stock.lot', 'LOT/Serial Number', domain="[('product_id','=',product_id)]")
    lot_id = fields.Many2one('stock.lot', 'LOT/Serial Number', domain="[('product_id','=',product_id)]")
    product_uom_id = fields.Many2one('uom.uom', 'Product Unit of Measure')
    product_uom_category_id = fields.Many2one(string='Uom category', related='product_uom_id.category_id', readonly=True)
    quant_id = fields.Many2one(comodel_name='stock.quant', string='Quant')

    '''
    ****************************************************************
    ************************FIELDS NOT USING END********************
    ****************************************************************
    '''
    company_id = fields.Many2one('res.company', 'Company', related='wastage_id.company_id', index=True, readonly=True, store=True)


    current_stock = fields.Float(string='Stock')

    adj_qty = fields.Float(string='Wastage Quantity')

    owner_id = fields.Many2one('res.partner', 'From Owner', check_company=True)

    # @api.onchange('quant_id')
    # def onchange_quant_id(self):
    #     print("\n\n\n\n")
    #     for line in self:
    #         current_stock = 0
    #         packaging_id = False
    #         if line.product_id and line.quant_id:
    #
    #             stock_qty = line.quant_id.quantity
    #             if stock_qty < 0.001:
    #                 raise UserError(_('Zero stock on this lot/expiry'))
    #
    #             primary_packaging_id = self.env['product.packaging'].search(
    #                 [('product_id', '=', line.product_id.id), ('primary_unit', '=', True)])
    #
    #             if not primary_packaging_id:
    #                 raise UserError(_('Primary/Stock keeping unit of measure is not defined for the selected product'))
    #
    #             packaging_id = primary_packaging_id.id
    #             packaging_qty = primary_packaging_id.qty
    #             current_stock = stock_qty/packaging_qty
    #
    #         line.current_stock = current_stock
    #         line.packaging_id = packaging_id

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            line.packaging_id = False
            line.current_stock = 0
            if line.product_id:
                # Find the primary packaging
                primary_packaging_id = self.env['product.packaging'].search(
                    [('product_id', '=', line.product_id.id), ('primary_unit', '=', True)], limit=1)
                if not primary_packaging_id:
                    raise UserError(_('Primary/Stock keeping unit of measure is not defined for the selected product %s.') % line.product_id.name)

                # Find the available stock in the selected location
                quants = self.env["stock.quant"].search(
                    [("product_id", "=", line.product_id.id),
                     ("location_id", "=", self.wastage_id.location_id.id),]
                )
                stock_qty = sum(quants.mapped("quantity"))
                print("/////////////////////////////////////***********************")
                print("quantssssss", quants, "stock_qty", stock_qty)
                packaging_qty = primary_packaging_id.qty
                current_stock = stock_qty / packaging_qty
                line.packaging_id = primary_packaging_id.id
                line.current_stock = current_stock
                print("line.current_stock", line.current_stock)
            else:
                line.packaging_id = False
                line.current_stock = 0

    @api.onchange('packaging_id')
    def _onchange_packaging_id(self):
        for line in self:
            current_stock = 0
            if line.product_id and line.packaging_id:
                quants = self.env["stock.quant"].search(
                    [("product_id", "=", line.product_id.id),
                     ("location_id", "=", self.wastage_id.location_id.id),]
                )
                stock_qty = sum(quants.mapped("quantity"))
                print("/////////////////////////////////////***********************")
                print("quantssssss", quants, "stock_qty", stock_qty)
                packaging_qty = line.packaging_id.qty
                current_stock = stock_qty / packaging_qty
            line.current_stock = current_stock
            print("line.current_stock", line.current_stock)


class StockMove(models.Model):
    _inherit = "stock.move"

    wastage_id = fields.Many2one(
        'pos.wastage', 'Inventory',
        index=True, ondelete='cascade')