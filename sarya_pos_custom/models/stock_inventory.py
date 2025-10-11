from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_utils, float_compare


class StockInventory(models.Model):
    _name = "stock.inventory"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _description = "Inventory"
    _order = "id desc"

    @api.model
    def _selection_filter(self):
        """ Get the list of filter allowed according to the options checked
        in 'Settings\Warehouse'. """
        res_filter = [
            ('none', _('All products')),
            ('category', _('One product category')),
            ('product', _('One product only')),
            ('partial', _('Select products manually'))]
        return res_filter

    name = fields.Char(string='Inventory Reference', readonly=True, required=True,
                       states={'draft': [('readonly', False)]},
                       default='new', copy=False)
    date = fields.Datetime(string='Inventory Date', readonly=True, required=True, default=fields.Datetime.now,
                           help="If the inventory adjustment is not validated, date at which the theoritical quantities have been checked.\n"
                                "If the inventory adjustment is validated, date at which the inventory adjustment has been validated.")
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
                                 default=lambda self: self.env.company)

    state = fields.Selection(string='Status', selection=[
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('progress', 'In Progress'),
        ('done', 'Validated')],
                             copy=False, index=True, readonly=True,
                             default='draft')
    location_id = fields.Many2one('stock.location', "Location")

    category_id = fields.Many2one('product.category', string="Product Category",
                                  help="Specify Product Category to focus your inventory on a particular Category."
                                  )
    product_id = fields.Many2one(comodel_name='product.product', string='Product',
                                 help="Specify Product to focus your inventory on a particular Product.")
    package_id = fields.Many2one('stock.quant.package', string='Package',
                                 help="Specify Pack to focus your inventory on a particular Pack.")
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True, tracking=True,
                                 help="Specify Owner to focus your inventory on a particular Owner.")
    line_ids = fields.One2many(
        'stock.inventory.line', 'inventory_id', string='Inventories',
        copy=True, readonly=False,
        states={'done': [('readonly', True)]})

    lot_id = fields.Many2one('stock.lot', string='Lot/Serial Number',
                             copy=False, readonly=True, states={'draft': [('readonly', False)]},
                             help="Specify LOT/Serial Number to focus your inventory on a particular Lot/Serial Number.")
    filter = fields.Selection(string='Inventory of', selection=[
        ('none', _('All products')),
        ('category', _('One product category')),
        ('product', _('One product only')),
        ('partial', _('Select products manually'))],
                              required=True,
                              default='none',
                              help="If you do an entire inventory, you can choose 'All Products' and it will prefill the inventory with the current stock.  If you only do some products  "
                                   "(e.g. Cycle Counting) you can choose 'Manual Selection of Products' and the system won't propose anything.  You can also let the "
                                   "system propose for a single product / lot /... ")
    total_qty = fields.Float('Total Quantity')

    exhausted = fields.Boolean('Include Exhausted Products', readonly=True, states={'draft': [('readonly', False)]})
    line_count = fields.Integer('Line Count', compute="compute_line_count", store=True)
    stock_move_ids = fields.One2many(
        'stock.move', 'inventory_id', string='Stock Moves')
    pos_config_id = fields.Many2one(
        comodel_name='pos.config',
        string='POS Outlet')

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if res.name == 'new':
            res.name = self.env['ir.sequence'].next_by_code('stock.inventory')
        return res

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('You cannot delete a record which is not in draft status'))
        return super(StockInventory, self).unlink()

    @api.onchange('filter')
    def _onchange_filter(self):
        if self.filter not in ('product', 'product_owner'):
            self.product_id = False
        if self.filter != 'lot':
            self.lot_id = False
        if self.filter not in ('owner', 'product_owner'):
            self.partner_id = False
        if self.filter != 'pack':
            self.package_id = False
        if self.filter != 'category':
            self.category_id = False
        if self.filter != 'product':
            self.exhausted = False
        if self.filter == 'product':
            self.exhausted = True
            if self.product_id:
                return {'domain': {'product_id': [('product_tmpl_id', '=', self.product_id.product_tmpl_id.id)]}}

    @api.onchange('pos_config_id')
    def _onchange_pos_config(self):
        if self.pos_config_id:
            picking_type_id = self.pos_config_id.picking_type_id
            self.location_id = picking_type_id and picking_type_id.default_location_src_id and picking_type_id.default_location_src_id.id or False
        else:
            self.location_id = False


    @api.depends('state')
    def compute_line_count(self):
        stock_quant = self.env['stock.quant']
        for rec in self:
            rec.line_count = stock_quant.search_count([('stock_inventory_id', '=', rec.id)])

    def _default_location_id(self):
        company_id = self.env.context.get('default_company_id') or self.env.company.id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_id)], limit=1)
        if warehouse:
            return warehouse.lot_stock_id.id
        else:
            return None

    def action_start(self):
        for inventory in self.filtered(lambda x: x.state not in ('done', 'cancel')):
            vals = {'state': 'progress', 'date': fields.Datetime.now()}
            if (inventory.filter != 'partial') and not inventory.line_ids:
                vals.update(
                    {'line_ids': [(0, 0, line_values) for line_values in inventory._get_inventory_lines_values()]})
            inventory.write(vals)
        for inv_line in self.line_ids:
            if inv_line.product_id:
                inv_line.price = inv_line.product_id.standard_price

    def _get_inventory_lines_values(self):
        # TDE CLEANME: is sql really necessary ? I don't think so
        locations = self.env['stock.location'].search([('id', 'in', [self._default_location_id()])])
        if self.location_id:
            locations = self.env['stock.location'].search([('id', 'child_of', [self.location_id.id])])

        domain = ' location_id in %s AND quantity != 0 AND active = TRUE'
        args = (tuple(locations.ids),)

        vals = []
        Product = self.env['product.product'].sudo()
        # Empty recordset of products available in stock_quants
        quant_products = self.env['product.product']
        # Empty recordset of products to filter
        products_to_filter = self.env['product.product']

        # case 0: Filter on company
        if self.company_id:
            domain += ' AND company_id = %s'
            args += (self.company_id.id,)

        # case 1: Filter on One owner only or One product for a specific owner
        if self.partner_id:
            domain += ' AND owner_id = %s'
            args += (self.partner_id.id,)
        # case 2: Filter on One Lot/Serial Number
        if self.lot_id:
            domain += ' AND lot_id = %s'
            args += (self.lot_id.id,)
        # case 3: Filter on One product
        if self.product_id:
            domain += ' AND product_id = %s'
            args += (self.product_id.id,)
            products_to_filter |= self.product_id
        # case 4: Filter on A Pack
        if self.package_id:
            domain += ' AND package_id = %s'
            args += (self.package_id.id,)
        # case 5: Filter on One product category + Exahausted Products
        if self.category_id:
            categ_products = Product.search([('categ_id', 'child_of', self.category_id.id)])
            domain += ' AND product_id = ANY (%s)'
            args += (categ_products.ids,)
            products_to_filter |= categ_products
        self.env.cr.execute("""SELECT sq.id as quant_id, sq.product_id, sum(sq.quantity) as product_qty, sq.location_id, sq.lot_id as prod_lot_id, sq.package_id, sq.owner_id as partner_id
            FROM stock_quant sq
            LEFT JOIN product_product
            ON product_product.id = sq.product_id
            WHERE %s
            GROUP BY quant_id, product_id, location_id, lot_id, package_id, partner_id """ % domain, args)

        for product_data in self.env.cr.dictfetchall():
            # replace the None the dictionary by False, because falsy values are tested later on
            for void_field in [item[0] for item in product_data.items() if item[1] is None]:
                product_data[void_field] = False
            product_data['theoretical_qty'] = product_data['product_qty']
            if product_data['product_id']:
                product_data['product_uom_id'] = Product.browse(product_data['product_id']).uom_id.id
                quant_products |= Product.browse(product_data['product_id'])
            vals.append(product_data)
        if self.exhausted:
            exhausted_vals = self._get_exhausted_inventory_line(products_to_filter, quant_products)
            vals.extend(exhausted_vals)
        return vals

    def _get_exhausted_inventory_line(self, products, quant_products):
        '''
        This function return inventory lines for exausted products
        :param products: products With Selected Filter.
        :param quant_products: products available in stock_quants
        '''
        vals = []
        exhausted_domain = [('type', 'not in', ('service', 'consu', 'digital'))]
        if products:
            exhausted_products = products - quant_products
            exhausted_domain += [('id', 'in', exhausted_products.ids)]
        else:
            exhausted_domain += [('id', 'not in', quant_products.ids)]
        exhausted_products = self.env['product.product'].search(exhausted_domain)
        for product in exhausted_products:
            vals.append({
                'inventory_id': self.id,
                'product_id': product.id,
                'location_id': self.location_id.id,
                'product_uom_id': product.uom_po_id.id,
            })
        return vals


    def action_validate(self):
        move_vals = []
        for inv_line in self.line_ids:

            print("\n\n\n===================================*******89999")
            print("inv_line.inventory_diff_quantity ==>> ", inv_line.inventory_diff_quantity)
            print("inv_line.quant_id ==>> ", inv_line.quant_id)
            print("inv_line.quant_id.product_uom_id ==>> ", inv_line.quant_id.product_uom_id)
            print("inv_line.quant_id.product_uom_id.rounding ==>> ", inv_line.quant_id.product_uom_id.rounding)

            if float_compare(inv_line.inventory_diff_quantity, 0, precision_rounding=inv_line.quant_id.product_uom_id.rounding) > 0:
                valu = inv_line.quant_id._get_inventory_move_values(inv_line.inventory_diff_quantity,
                                                     inv_line.quant_id.product_id.with_company(
                                                         inv_line.quant_id.company_id).property_stock_inventory,
                                                     inv_line.quant_id.location_id, package_dest_id=inv_line.quant_id.package_id)
                valu['name'] = "Stock Update (Wastage Calculation) " + str(self.name)
                valu['inventory_id'] = self.id
                move_vals.append(valu)
            else:
                valu = inv_line.quant_id._get_inventory_move_values(-inv_line.inventory_diff_quantity,
                                                     inv_line.quant_id.location_id,
                                                     inv_line.quant_id.product_id.with_company(
                                                         inv_line.quant_id.company_id).property_stock_inventory,
                                                     package_id=inv_line.quant_id.package_id)
                valu['name'] = "Stock Bulk Update " + str(self.name)
                valu['inventory_id'] = self.id
                move_vals.append(valu)

        moves = self.env['stock.move'].with_context(inventory_mode=False).create(move_vals)
        moves._action_done()
        self.write({'state': 'done', 'date': fields.Datetime.now()})

    def action_reset_product_qty(self):
        self.mapped('line_ids').write({'product_qty': 0})

    def action_cancel_draft(self):
        if self.state != 'done':
            self.write({'line_ids': [(5,)], 'state': 'draft'})



class InventoryLine(models.Model):
    _name = "stock.inventory.line"
    _description = "Inventory Line"
    _order = "product_id, inventory_id, location_id, prod_lot_id"

    inventory_id = fields.Many2one(
        'stock.inventory', 'Inventory',
        index=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', 'Owner')
    product_id = fields.Many2one(
        'product.product', 'Product',
        domain=[('type', '=', 'product')],
        index=True, required=True)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Product Unit of Measure',
    )
    product_uom_category_id = fields.Many2one(string='Uom category', related='product_uom_id.category_id',
                                              readonly=True)
    location_id = fields.Many2one(
        'stock.location', 'Location',
        index=True, )
    package_id = fields.Many2one(
        'stock.quant.package', 'Pack', index=True)
    prod_lot_id = fields.Many2one(
        'stock.lot', 'LOT/Serial Number',
        domain="[('product_id','=',product_id)]")
    company_id = fields.Many2one(
        'res.company', 'Company', related='inventory_id.company_id',
        index=True, readonly=True, store=True)
    # TDE FIXME: necessary ? -> replace by location_id
    state = fields.Selection(
        'Status', related='inventory_id.state', readonly=True)
    product_qty = fields.Float(
        'Checked Quantity',
        digits='Product Unit of Measure', default=0)
    theoretical_qty = fields.Float(
        'Theoretical Quantity',
        digits='Product Unit of Measure', readonly=True)
    inventory_diff_quantity = fields.Float(
        'Difference', compute='_compute_inventory_diff_quantity',
        help="Indicates the gap between the product's theoretical quantity and its counted quantity.",
        readonly=True, digits='Product Unit of Measure')
    inventory_location_id = fields.Many2one(
        'stock.location', 'Inventory Location', related='inventory_id.location_id', related_sudo=False, readonly=False)
    product_tracking = fields.Selection('Tracking', related='product_id.tracking', readonly=True)
    price = fields.Float('Price')
    quant_id = fields.Many2one(
        comodel_name='stock.quant',
        string='Quant')

    primary_packaging_id = fields.Many2one('product.packaging', 'Primary Package', compute='_find_primary_package')

    def _find_primary_package(self):
        for line in self:
            primary_packaging_id = False
            for pack in line.product_id.packaging_ids:
                if pack.primary_unit:
                    primary_packaging_id = pack.id
            line.primary_packaging_id = primary_packaging_id

    @api.onchange('product_id')
    def _get_inventory_details(self):
        """If Inventory of is Select product Manually, automatically load UOM and Location while select product"""
        for line in self:
            if line.inventory_id.filter == 'partial':
                if line.product_id:
                    line.product_uom_id = line.product_id.uom_po_id.id
                    line.location_id = line.inventory_id.location_id.id
                    line.price = line.product_id.standard_price

    @api.onchange('location_id')
    def _get_theoretical_qty(self):
        for rec in self:
            if rec.location_id and rec.inventory_id.state == 'progress' and rec.product_id:
                rec.theoretical_qty = rec.product_id.with_context(location=rec.location_id.ids).qty_available

    @api.depends('theoretical_qty')
    def _compute_inventory_diff_quantity(self):
        for quant in self:
            quant.inventory_diff_quantity = quant.product_qty - quant.theoretical_qty

    # def _get_move_values(self, qty, location_id, location_dest_id, out):
    #     self.ensure_one()
    #     return {
    #         'name': _('INV:') + (self.inventory_id.name or ''),
    #         'product_id': self.product_id.id,
    #         'product_uom': self.product_uom_id.id,
    #         'product_uom_qty': self.product_qty - self.theoretical_qty,
    #         'date': self.inventory_id.date,
    #         'company_id': self.inventory_id.company_id.id,
    #         'inventory_id': self.inventory_id.id,
    #         # 'state': 'confirmed',
    #         'restrict_partner_id': self.partner_id.id,
    #         'location_id': location_id,
    #         'location_dest_id': location_dest_id,
    #         'is_inventory': True,
    #         'price_unit': self.price,
    #         'move_line_ids': [(0, 0, {
    #             'product_id': self.product_id.id,
    #             'lot_id': self.prod_lot_id.id,
    #             'product_uom_id': self.product_uom_id.id,
    #             'quantity': self.product_qty - self.theoretical_qty,
    #             'quantity_product_uom': self.product_qty - self.theoretical_qty,
    #             'package_id': out and self.package_id.id or False,
    #             'result_package_id': (not out) and self.package_id.id or False,
    #             'location_id': location_id,
    #             'location_dest_id': location_dest_id,
    #             'owner_id': self.partner_id.id,
    #         })]
    #     }
    #
    # def _generate_moves(self):
    #     vals_list = []
    #     for line in self:
    #         if float_utils.float_compare(line.theoretical_qty, line.product_qty,
    #                                      precision_rounding=line.product_id.uom_id.rounding) == 0:
    #             continue
    #         diff = line.theoretical_qty - line.product_qty
    #         if diff < 0:  # found more than expected
    #             vals = line._get_move_values(abs(diff), line.product_id.property_stock_inventory.id,
    #                                          line.location_id.id, False)
    #         else:
    #             vals = line._get_move_values(abs(diff), line.location_id.id,
    #                                          line.product_id.property_stock_inventory.id, True)
    #         print('vals >>>>>', vals)
    #         vals_list.append(vals)
    #     return self.env['stock.move'].with_context(inventory_mode=False).create(vals_list)


class StockMove(models.Model):
    _inherit = 'stock.move'

    inventory_id = fields.Many2one('stock.inventory', 'Inventory')
