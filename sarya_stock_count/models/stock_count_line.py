# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class StockCountLine(models.Model):
    _name = "stock.count.line"
    _description = "Stock Count Line"
    _order = "product_id, stock_count_id, location_id"

    stock_count_id = fields.Many2one(
        comodel_name='stock.count',
        string='Inventory',
        index=True,
        ondelete='cascade'
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        domain=[('type', '=', 'product')],
        index=True,
        required=True
    )
    product_name = fields.Char(
        string='Product Name',
        related='product_id.display_name'
    )
    location_id = fields.Many2one(
        comodel_name='stock.location',
        string='Location',
        index=True
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        related='stock_count_id.company_id',
        index=True,
        readonly=True,
        store=True
    )
    state = fields.Selection(
        string='Status',
        related='stock_count_id.state',
        readonly=True
    )
    opening_qty = fields.Float(
        string='Opening Qty',
        digits='Product Unit of Measure',
        compute="_compute_opening_qty",
        store=True
    )
    grn_qty = fields.Float(
        string='GRN Qty',
        digits='Product Unit of Measure',
        compute="_compute_grn_qty",
        store=True
    )
    transfer_in_qty = fields.Float(
        string='Transfer In Qty',
        digits='Product Unit of Measure',
        compute="_compute_transfer_in_qty",
        store=True
    )
    transfer_out_qty = fields.Float(
        string='Transfer Out Qty',
        digits='Product Unit of Measure',
        compute="_compute_transfer_out_qty",
        store=True
    )
    wastage_qty = fields.Float(
        string='Wastage Qty',
        digits='Product Unit of Measure',
        compute="_compute_wastage_qty",
        store=True
    )
    adjustment_qty = fields.Float(
        string='Adjustment Qty',
        digits='Product Unit of Measure',
        compute="_compute_adjustment_qty",
        store=True
    )
    production_qty = fields.Float(
        string='Production Qty',
        digits='Product Unit of Measure',
        compute="_compute_production_qty",
        store=True
    )
    sale_qty = fields.Float(
        string='Sale Qty',
        digits='Product Unit of Measure',
        compute="_compute_sale_qty",
        store=True
    )
    sale_return_qty = fields.Float(
        string='Sale Return Qty',
        digits='Product Unit of Measure',
        compute="_compute_sale_return_qty",
        store=True
    )
    theoretical_qty = fields.Float(
        string='Theoretical Qty',
        digits='Product Unit of Measure',
        compute="_compute_theoretical_qty",
        store=True
    )
    counted_qty = fields.Float(
        string='Counted Qty',
        digits='Product Unit of Measure',
        default=0
    )
    stock_diff_quantity = fields.Float(
        string='Difference',
        compute='_compute_stock_diff_quantity',
        help="Indicates the gap between the product's theoretical quantity and its counted quantity.",
        readonly=True,
        digits='Product Unit of Measure'
    )
    price = fields.Float(
        string='Price'
    )
    primary_packaging_id = fields.Many2one(
        comodel_name='product.packaging', string='Primary Package',
        compute='_find_primary_package'
    )
    is_counted_qty_entered = fields.Boolean(
        string='Is Real Qty Entered?',
        default=False
    )

    def check_previous_stock_count_record(self):
        domain = [
            ('product_id', '=', self.product_id.id),
            ('stock_count_id.pos_config_id', '=', self.stock_count_id.pos_config_id.id),
            ('location_id', '=', self.location_id.id),
            ('state', '=', 'done'),
            ('is_counted_qty_entered', '=', True),
            ('id', '!=', self.id),
        ]
        previous_stock_count_obj = self.env['stock.count.line'].sudo().search(domain, order='id desc', limit=1)
        return previous_stock_count_obj

    @api.depends('product_id', 'location_id')
    def _compute_opening_qty(self):
        for rec in self:
            previous_stock_count_obj = rec.check_previous_stock_count_record()
            if previous_stock_count_obj:
                rec.opening_qty = previous_stock_count_obj.counted_qty
            else:
                rec.opening_qty = 0

    @api.depends('product_id', 'location_id')
    def _compute_grn_qty(self):
        supplier_loc = self.env.ref('stock.stock_location_suppliers')
        StockMoveLine = self.env['stock.move.line'].sudo()

        for rec in self:
            if not rec.product_id or not rec.location_id:
                rec.grn_qty = 0.0
                continue

            # Get previous stock count datetime
            previous_stock_count_obj = rec.check_previous_stock_count_record()
            start_dt = previous_stock_count_obj.stock_count_id.validated_date if previous_stock_count_obj and previous_stock_count_obj.stock_count_id else False

            # Current inventory datetime (your own field)
            end_dt = rec.stock_count_id.date if rec.stock_count_id and rec.stock_count_id.date else False

            domain_in = [
                ('product_id', '=', rec.product_id.id),
                ('location_id', '=', supplier_loc.id),
                ('location_dest_id', '=', rec.location_id.id),
                ('state', '=', 'done'),
            ]

            domain_out = [
                ('product_id', '=', rec.product_id.id),
                ('location_id', '=', rec.location_id.id),
                ('location_dest_id', '=', supplier_loc.id),
                ('state', '=', 'done'),
            ]

            # Add start datetime
            if start_dt:
                domain_in.append(('date', '>=', start_dt))
                domain_out.append(('date', '>=', start_dt))

            # Add end datetime
            if end_dt:
                domain_in.append(('date', '<=', end_dt))
                domain_out.append(('date', '<=', end_dt))

            incoming_qty = sum(StockMoveLine.search(domain_in).mapped('quantity'))
            outgoing_qty = sum(StockMoveLine.search(domain_out).mapped('quantity'))

            rec.grn_qty = incoming_qty - outgoing_qty

    @api.depends('product_id', 'location_id')
    def _compute_transfer_in_qty(self):
        StockMoveLine = self.env['stock.move.line'].sudo()
        other_internal_locations = self.env['stock.location'].search(
            [('usage', '=', 'internal'), ('id', '!=', self.location_id.id)])
        for rec in self:
            if not rec.product_id or not rec.location_id:
                rec.transfer_in_qty = 0.0
                continue

            # Get previous stock count datetime
            previous_stock_count_obj = rec.check_previous_stock_count_record()
            start_dt = previous_stock_count_obj.stock_count_id.validated_date if previous_stock_count_obj and previous_stock_count_obj.stock_count_id else False

            # Current inventory datetime (your own field)
            end_dt = rec.stock_count_id.date if rec.stock_count_id and rec.stock_count_id.date else False

            domain_in = [
                ('product_id', '=', rec.product_id.id),
                ('location_id', 'in', other_internal_locations.ids),
                ('location_dest_id', '=', rec.location_id.id),
                ('state', '=', 'done'),
            ]

            # Add start datetime
            if start_dt:
                domain_in.append(('date', '>=', start_dt))

            # Add end datetime
            if end_dt:
                domain_in.append(('date', '<=', end_dt))

            incoming_qty = sum(StockMoveLine.search(domain_in).mapped('quantity'))
            rec.transfer_in_qty = incoming_qty

    @api.depends('product_id', 'location_id')
    def _compute_transfer_out_qty(self):
        StockMoveLine = self.env['stock.move.line'].sudo()
        other_internal_locations = self.env['stock.location'].search(
            [('usage', '=', 'internal'), ('id', '!=', self.location_id.id)])
        for rec in self:
            if not rec.product_id or not rec.location_id:
                rec.transfer_out_qty = 0.0
                continue

            # Get previous stock count datetime
            previous_stock_count_obj = rec.check_previous_stock_count_record()
            start_dt = previous_stock_count_obj.stock_count_id.validated_date if previous_stock_count_obj and previous_stock_count_obj.stock_count_id else False

            # Current inventory datetime (your own field)
            end_dt = rec.stock_count_id.date if rec.stock_count_id and rec.stock_count_id.date else False

            domain_out = [
                ('product_id', '=', rec.product_id.id),
                ('location_id', '=', rec.location_id.id),
                ('location_dest_id', 'in', other_internal_locations.ids),
                ('state', '=', 'done'),
            ]

            # Add start datetime
            if start_dt:
                domain_out.append(('date', '>=', start_dt))

            # Add end datetime
            if end_dt:
                domain_out.append(('date', '<=', end_dt))

            outgoing_qty = sum(StockMoveLine.search(domain_out).mapped('quantity'))
            rec.transfer_out_qty = outgoing_qty

    @api.depends('product_id', 'location_id')
    def _compute_wastage_qty(self):
        StockMoveLine = self.env['stock.move.line'].sudo()
        # locations = self.env['stock.location'].sudo().search([('usage', '=', 'inventory')])
        locations = self.env['stock.location'].search([
            ('usage', '=', 'inventory'), ('scrap_location', '=', True), ('company_id', '=', self.env.company.id)],
            limit=1)

        for rec in self:
            if not rec.product_id or not rec.location_id:
                rec.wastage_qty = 0.0
                continue

            # Get previous stock count datetime
            previous_stock_count_obj = rec.check_previous_stock_count_record()
            start_dt = previous_stock_count_obj.stock_count_id.validated_date if previous_stock_count_obj and previous_stock_count_obj.stock_count_id else False

            # Current inventory datetime (your own field)
            end_dt = rec.stock_count_id.date if rec.stock_count_id and rec.stock_count_id.date else False

            domain = [
                ('product_id', '=', rec.product_id.id),
                ('location_id', '=', rec.location_id.id),
                ('location_dest_id', 'in', locations.ids),
                ('state', '=', 'done'),
            ]

            # Add start datetime
            if start_dt:
                domain.append(('date', '>=', start_dt))

            # Add end datetime
            if end_dt:
                domain.append(('date', '<=', end_dt))

            wastage_qty = sum(StockMoveLine.search(domain).mapped('quantity'))
            rec.wastage_qty = wastage_qty

    @api.depends('product_id', 'location_id')
    def _compute_adjustment_qty(self):
        StockMoveLine = self.env['stock.move.line'].sudo()
        # locations = self.env['stock.location'].sudo().search([('usage', '=', 'inventory')])
        locations = self.env['stock.location'].search([
            ('usage', '=', 'inventory'), ('scrap_location', '=', False), ('company_id', '=', self.env.company.id)],
            limit=1)

        for rec in self:
            if not rec.product_id or not rec.location_id:
                rec.adjustment_qty = 0.0
                continue

            # Get previous stock count datetime
            previous_stock_count_obj = rec.check_previous_stock_count_record()
            start_dt = previous_stock_count_obj.stock_count_id.validated_date if previous_stock_count_obj and previous_stock_count_obj.stock_count_id else False

            # Current inventory datetime (your own field)
            end_dt = rec.stock_count_id.date if rec.stock_count_id and rec.stock_count_id.date else False

            domain_in = [
                ('product_id', '=', rec.product_id.id),
                ('location_id', '=', rec.location_id.id),
                ('location_dest_id', 'in', locations.ids),
                ('state', '=', 'done'),
            ]

            domain_out = [
                ('product_id', '=', rec.product_id.id),
                ('location_id', 'in', locations.ids),
                ('location_dest_id', '=', rec.location_id.id),
                ('state', '=', 'done'),
            ]

            # Add start datetime
            if start_dt:
                domain_in.append(('date', '>=', start_dt))
                domain_out.append(('date', '>=', start_dt))

            # Add end datetime
            if end_dt:
                domain_in.append(('date', '<=', end_dt))
                domain_out.append(('date', '<=', end_dt))

            adjustment_in_qty = sum(StockMoveLine.search(domain_in).mapped('quantity'))
            adjustment_out_qty = sum(StockMoveLine.search(domain_out).mapped('quantity'))
            rec.adjustment_qty = -(adjustment_in_qty - adjustment_out_qty)

    @api.depends('product_id', 'location_id')
    def _compute_production_qty(self):
        StockMoveLine = self.env['stock.move.line'].sudo()
        locations = self.env['stock.location'].sudo().search([('usage', 'in', ['production'])])

        for rec in self:
            if not rec.product_id or not rec.location_id:
                rec.production_qty = 0.0
                continue

            # Get previous stock count datetime
            previous_stock_count_obj = rec.check_previous_stock_count_record()
            start_dt = previous_stock_count_obj.stock_count_id.validated_date if previous_stock_count_obj and previous_stock_count_obj.stock_count_id else False

            # Current inventory datetime (your own field)
            end_dt = rec.stock_count_id.date if rec.stock_count_id and rec.stock_count_id.date else False

            domain_in = [
                ('product_id', '=', rec.product_id.id),
                ('location_id', '=', rec.location_id.id),
                ('location_dest_id', 'in', locations.ids),
                ('state', '=', 'done'),
            ]

            domain_out = [
                ('product_id', '=', rec.product_id.id),
                ('location_id', 'in', locations.ids),
                ('location_dest_id', '=', rec.location_id.id),
                ('state', '=', 'done'),
            ]

            # Add start datetime
            if start_dt:
                domain_in.append(('date', '>=', start_dt))
                domain_out.append(('date', '>=', start_dt))

            # Add end datetime
            if end_dt:
                domain_in.append(('date', '<=', end_dt))
                domain_out.append(('date', '<=', end_dt))

            production_in_qty = sum(StockMoveLine.search(domain_in).mapped('quantity'))
            product_out_qty = sum(StockMoveLine.search(domain_out).mapped('quantity'))
            rec.production_qty = -(production_in_qty - product_out_qty)

    @api.depends('product_id', 'location_id')
    def _compute_sale_qty(self):
        customer_loc = self.env.ref('stock.stock_location_customers')
        StockMoveLine = self.env['stock.move.line'].sudo()

        for rec in self:
            if not rec.product_id or not rec.location_id:
                rec.sale_qty = 0.0
                continue

            # Get previous stock count datetime
            previous_stock_count_obj = rec.check_previous_stock_count_record()
            start_dt = previous_stock_count_obj.stock_count_id.validated_date if previous_stock_count_obj and previous_stock_count_obj.stock_count_id else False

            # Current inventory datetime (your own field)
            end_dt = rec.stock_count_id.date if rec.stock_count_id and rec.stock_count_id.date else False

            domain = [
                ('product_id', '=', rec.product_id.id),
                ('location_id', '=', rec.location_id.id),
                ('location_dest_id', '=', customer_loc.id),
                ('state', '=', 'done'),
            ]

            # Add start datetime
            if start_dt:
                domain.append(('date', '>=', start_dt))

            # Add end datetime
            if end_dt:
                domain.append(('date', '<=', end_dt))

            sale_qty = sum(StockMoveLine.search(domain).mapped('quantity'))
            rec.sale_qty = sale_qty

    @api.depends('product_id', 'location_id')
    def _compute_sale_return_qty(self):
        customer_loc = self.env.ref('stock.stock_location_customers')
        StockMoveLine = self.env['stock.move.line'].sudo()

        for rec in self:
            if not rec.product_id or not rec.location_id:
                rec.sale_qty = 0.0
                continue

            # Get previous stock count datetime
            previous_stock_count_obj = rec.check_previous_stock_count_record()
            start_dt = previous_stock_count_obj.stock_count_id.validated_date if previous_stock_count_obj and previous_stock_count_obj.stock_count_id else False

            # Current inventory datetime (your own field)
            end_dt = rec.stock_count_id.date if rec.stock_count_id and rec.stock_count_id.date else False

            domain = [
                ('product_id', '=', rec.product_id.id),
                ('location_id', '=', customer_loc.id),
                ('location_dest_id', '=', rec.location_id.id),
                ('state', '=', 'done'),
            ]

            # Add start datetime
            if start_dt:
                domain.append(('date', '>=', start_dt))

            # Add end datetime
            if end_dt:
                domain.append(('date', '<=', end_dt))

            sale_return_qty = sum(StockMoveLine.search(domain).mapped('quantity'))
            rec.sale_return_qty = sale_return_qty

    @api.depends('opening_qty', 'grn_qty', 'transfer_in_qty', 'transfer_out_qty', 'wastage_qty', 'adjustment_qty',
                 'sale_qty', 'sale_return_qty')
    def _compute_theoretical_qty(self):
        for rec in self:
            rec.theoretical_qty = rec.opening_qty + rec.grn_qty + rec.transfer_in_qty + rec.sale_return_qty + rec.adjustment_qty - rec.transfer_out_qty - rec.wastage_qty - rec.sale_qty

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
            if line.product_id:
                line.location_id = line.stock_count_id.location_id.id
                line.price = line.product_id.standard_price

    @api.onchange('counted_qty')
    def _onchange_counted_qty(self):
        for line in self:
            line.is_counted_qty_entered = True

    @api.depends('theoretical_qty', 'counted_qty', 'is_counted_qty_entered')
    def _compute_stock_diff_quantity(self):
        for rec in self:
            if rec.is_counted_qty_entered:
                rec.stock_diff_quantity = rec.counted_qty - rec.theoretical_qty
            else:
                rec.stock_diff_quantity = 0
