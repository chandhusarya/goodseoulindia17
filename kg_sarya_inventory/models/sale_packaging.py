# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from datetime import datetime, timedelta


class SaleOrderLineInh(models.Model):
    _inherit = 'sale.order.line'

    pkg_unit_price = fields.Float("PKG Unit Price")
    product_packaging_qty = fields.Float('Qty', default=1)

    package_received = fields.Float(string="Package Delivered", compute='_compute_package_received')
    package_billed = fields.Float(string="Package Invoiced", compute='_compute_package_billed')

    package_received_store = fields.Float(string="Package Delivered")
    package_billed_store = fields.Float(string="Package Invoiced")

    def compute_pkg_details(self, par):
        if self.product_packaging_id.primary_unit:
            packaging_id = self.product_packaging_id.name
            ordered_qty = self.product_packaging_qty
            delivered_qty = self.package_received
        else:
            primary = self.product_id.packaging_ids.search([('primary_unit', '=', True)])
            if len(primary) > 0:
                for prime in primary:
                    packaging_id = prime.name
                    ordered_qty = (self.product_packaging_qty * self.product_packaging_id.qty) / prime.qty
                    ordered_qty = str(round(ordered_qty, 2))
                    delivered_qty = (self.package_received * self.product_packaging_id.qty) / prime.qty
                    delivered_qty = str(round(delivered_qty, 2))
            else:
                packaging_id = self.product_packaging_id.name
                ordered_qty = self.product_packaging_qty
                delivered_qty = self.package_received
        if par == 1:
            return packaging_id
        if par == 2:
            return ordered_qty
        if par == 3:
            return delivered_qty
        print(self)
        print("inside-------->>", par)

    @api.depends('product_id', 'product_packaging_id')
    def _compute_package_received(self):
        for line in self:
            package = self.env['product.packaging'].search(
                [('product_id', '=', line.product_id.id), ('id', '=', line.product_packaging_id.id)])
            # print(package)
            if line.qty_delivered != 0 and package.qty > 0:
                line.package_received = line.qty_delivered / package.qty
                line.package_received_store = line.qty_delivered / package.qty
            else:
                line.package_received = 0
                line.package_received_store = 0

    @api.depends('product_id', 'product_packaging_id')
    def _compute_package_billed(self):
        for line in self:
            package = self.env['product.packaging'].search(
                [('product_id', '=', line.product_id.id), ('id', '=', line.product_packaging_id.id)])
            # print(package)
            if package and line.qty_invoiced:
                line.package_billed = line.qty_invoiced / package.qty
                line.package_billed_store = line.qty_invoiced / package.qty
            else:
                line.package_billed = 0
                line.package_billed_store = 0

    def _prepare_invoice_line(self, **optional_values):
        """This method is overrided to include package details"""
        """
        Prepare the dict of values to create the new invoice line for a sales order line.

        :param qty: float quantity to invoice
        :param optional_values: any parameter that should be added to the returned invoice line
        """
        self.ensure_one()
        res = {
            'display_type': self.display_type or 'product',
            'sequence': self.sequence,
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'quantity': self.qty_delivered,
            'discount': self.discount,
            'price_unit': self.price_unit,
            'tax_ids': [(6, 0, self.tax_id.ids)],
            #'analytic_account_id': self.order_id.analytic_account_id.id,
            #'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
            'sale_line_ids': [(4, self.id)],
            'package_id': self.product_packaging_id.id,
            'product_packaging_qty': self.package_received,
            'pkg_unit_price': self.pkg_unit_price,
            'promo': self.pricelist_item_id.promo,
        }
        if optional_values:
            res.update(optional_values)
        if self.display_type:
            res['account_id'] = False
        return res

    @api.onchange('product_id', 'product_uom_qty', 'product_uom')
    def _onchange_suggest_packaging(self):
        # remove packaging if not match the product
        if self.product_packaging_id.product_id != self.product_id:
            self.product_packaging_id = False

    # @api.onchange('product_packaging_id')
    # def _onchange_product_packaging_id(self):
    #     if self.product_packaging_id and self.product_uom_qty:
    #         newqty = self.product_packaging_id._check_qty(self.product_uom_qty, self.product_uom, "UP")

    # @api.onchange('pkg_unit_price','product_packaging_qty, ')
    # def _onchange_pkg_unit_price(self):
    #   if self.pkg_unit_price and self.product_packaging_qty:
    #       self.price_unit = self.pkg_unit_price/self.product_packaging_id.qty

    def compute_price_rule_get_package_items(self, date, prod_tmpl_ids, pricelist_id, packaging_id):
        self.ensure_one()
        # Load all rules
        #self.env['product.pricelist.item'].flush(['price', 'currency_id', 'company_id'])
        self.env.cr.execute(
            """
            SELECT
                item.id
            FROM
                product_pricelist_item AS item
            WHERE
                (item.product_tmpl_id IS NULL OR item.product_tmpl_id = any(%s))
                AND (item.pricelist_id = %s)
                AND (item.packging_id = %s)
                AND (item.date_start<=%s)
                AND (item.date_end>=%s)
            """,
            (prod_tmpl_ids, pricelist_id, packaging_id, date, date))

        item_ids = [x[0] for x in self.env.cr.fetchall()]
        if len(item_ids) > 0:
            return self.env['product.pricelist.item'].browse(item_ids)
        else:
            #self.env['product.pricelist.item'].flush(['price', 'currency_id', 'company_id'])
            self.env.cr.execute(
                """
                SELECT
                    item.id
                FROM
                    product_pricelist_item AS item
                WHERE
                    (item.product_tmpl_id IS NULL OR item.product_tmpl_id = any(%s))
                    AND (item.pricelist_id = %s)
                    AND (item.packging_id = %s)
                    AND (item.date_start IS NULL)
                    AND (item.date_end IS NULL)
                """,
                (prod_tmpl_ids, pricelist_id, packaging_id))

            item_ids = [x[0] for x in self.env.cr.fetchall()]
            return self.env['product.pricelist.item'].browse(item_ids)

    @api.onchange('product_packaging_qty', 'product_packaging_id', 'pkg_unit_price')
    def _onchange_pkg_qty(self):
        if self.product_packaging_qty and self.product_packaging_id:
            # SQL query to search pricelist in range
            if len(self.order_id.pricelist_id) == 1:
                pricelists = self.compute_price_rule_get_package_items \
                    (self.order_id.date_order, [self.product_id.product_tmpl_id.id], self.order_id.pricelist_id.id,
                     self.product_packaging_id.id)
                if pricelists:
                    self.pkg_unit_price = pricelists[0].fixed_price
                    self.pricelist_item_id = pricelists[0].id

                else:
                    self.pkg_unit_price = 0
            else:
                self.pkg_unit_price = 0
        if self.pkg_unit_price and self.product_packaging_id:
            self.price_unit = self.pkg_unit_price / self.product_packaging_id.qty
        elif self.pkg_unit_price == 0:
            self.price_unit = 0.0

    @api.constrains('pkg_unit_price')
    def _check_pkg_unit_price(self):
        for rec in self:
            if rec.pkg_unit_price == 0.00 and not rec.order_id.pricelist_id.special:
                raise ValidationError(_("Package unit Price can not be null"))

    @api.onchange('product_packaging_id', 'product_uom', 'product_uom_qty')
    def _onchange_update_product_packaging_qty(self):
        if not self.product_packaging_id:
            self.product_packaging_qty = False
        else:
            packaging_uom = self.product_packaging_id.product_uom_id
            packaging_uom_qty = self.product_uom._compute_quantity(self.product_uom_qty, packaging_uom)
            self.name = self.product_packaging_id.barcode + "-" + self.product_packaging_id.description if self.product_packaging_id.barcode else self.product_packaging_id.description
            self.product_uom_qty = self.product_packaging_qty * self.product_packaging_id.qty

    # @api.onchange('product_packaging_id')
    # def _set_pricelist_line_item(self):
    #     """linking price list item with sale order line"""
    #     if self.order_id.pricelist_id and self.product_packaging_id:
    #         pr_item = self.env['product.pricelist.item'].search([('product_tmpl_id','=',self.product_id.product_tmpl_id.id),('pricelist_id','=',self.order_id.pricelist_id.id),('fixed_price','=',self.pkg_unit_price)],limit=1)
    #         print("pr_item---->>>%s",pr_item)
    #         if len(pr_item)>0:
    #             self.pricelist_item_id = pr_item.id
    #             print(self.pricelist_item_id)
    #             print("ok--------------")

    @api.onchange('product_uom', 'product_uom_qty')
    def product_uom_change(self):
        """ Override original function to not calculate unit price from pricelist again"""
        if not self.product_uom or not self.product_id:
            self.price_unit = 0.0
            return
        if self.order_id.pricelist_id and self.order_id.partner_id:
            product = self.product_id.with_context(
                lang=self.order_id.partner_id.lang,
                partner=self.order_id.partner_id,
                quantity=self.product_uom_qty,
                date=self.order_id.date_order,
                pricelist=self.order_id.pricelist_id.id,
                uom=self.product_uom.id,
                fiscal_position=self.env.context.get('fiscal_position')
            )
            if not self.product_packaging_qty:
                line = self.with_company(self.company_id)
                price = self._get_display_price()
                self.price_unit = self.product_id._get_tax_included_unit_price(
                    self.company_id or self.env.company,
                    self.order_id.currency_id,
                    self.order_id.date_order,
                    'sale',
                    fiscal_position=self.order_id.fiscal_position_id,
                    product_price_unit=price,
                    product_currency=self.currency_id
                )

    def _prepare_procurement_values(self, group_id=False):
        """ Prepare specific key for moves or other components that will be created from a stock rule
        comming from a sale order line. This method could be override in order to add other custom key that could
        be used in move/po creation.
        """
        values = super(SaleOrderLineInh, self)._prepare_procurement_values(group_id)
        self.ensure_one()
        # Use the delivery date if there is else use date_order and lead time
        date_deadline = self.order_id.commitment_date or (
                self.order_id.date_order + timedelta(days=self.customer_lead or 0.0))
        date_planned = date_deadline - timedelta(days=self.order_id.company_id.security_lead)
        values.update({
            'group_id': group_id,
            'description_picking': self.name,
            'sale_line_id': self.id,
            'date_planned': date_planned,
            'date_deadline': date_deadline,
            'route_ids': self.route_id,
            'warehouse_id': self.order_id.warehouse_id or False,
            'partner_id': self.order_id.partner_shipping_id.id,
            'product_description_variants': self._get_sale_order_line_multiline_description_variants(),
            'company_id': self.order_id.company_id,
            'product_packaging_id': self.product_packaging_id,
            'pkg_demand': self.product_packaging_qty if self.product_packaging_qty else '',
            'pkg_done': self.product_packaging_qty if self.product_packaging_qty else '',
            'picking_type_id': self.order_id.picking_type_id.id or False,
            # 'quantity_done':self.product_uom_qty,
        })
        return values


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_stock_move_values_false(self, product_id, product_qty, product_uom, location_id, name, origin, company_id,
                               values):
        """Override original function"""
        group_id = False
        if self.group_propagation_option == 'propagate':
            group_id = values.get('group_id', False) and values['group_id'].id
        elif self.group_propagation_option == 'fixed':
            group_id = self.group_id.id

        date_scheduled = fields.Datetime.to_string(
            fields.Datetime.from_string(values['date_planned']) - relativedelta(days=self.delay or 0)
        )
        date_deadline = values.get('date_deadline') and (
                fields.Datetime.to_datetime(values['date_deadline']) - relativedelta(days=self.delay or 0)) or False
        partner = self.partner_address_id or (values.get('group_id', False) and values['group_id'].partner_id)
        if partner:
            product_id = product_id.with_context(lang=partner.lang or self.env.user.lang)
        picking_description = product_id._get_description(self.picking_type_id)
        if values.get('product_description_variants'):
            picking_description += values['product_description_variants']
        # it is possible that we've already got some move done, so check for the done qty and create
        # a new move with the correct qty
        qty_left = product_qty

        move_dest_ids = []
        if not self.location_id.should_bypass_reservation():
            move_dest_ids = values.get('move_dest_ids', False) and [(4, x.id) for x in values['move_dest_ids']] or []

        # when create chained moves for inter-warehouse transfers, set the warehouses as partners
        if not partner and move_dest_ids:
            move_dest = values['move_dest_ids']
            if location_id == company_id.internal_transit_location_id:
                partners = move_dest.location_dest_id.warehouse_id.partner_id
                if len(partners) == 1:
                    partner = partners
                    move_dest.partner_id = partner

        move_values = {
            'name': name[:2000],
            'company_id': self.company_id.id or self.location_src_id.company_id.id or self.location_id.company_id.id or company_id.id,
            'product_id': product_id.id,
            'product_uom': product_uom.id,
            'product_uom_qty': qty_left,
            'partner_id': partner.id if partner else False,
            'location_id': self.location_src_id.id,
            'location_dest_id': location_id.id,
            'move_dest_ids': move_dest_ids,
            'rule_id': self.id,
            'procure_method': self.procure_method,
            'origin': origin,
            # 'picking_type_id': self.picking_type_id.id,
            'group_id': group_id,
            'route_ids': [(4, route.id) for route in values.get('route_ids', [])],
            'warehouse_id': self.propagate_warehouse_id.id or self.warehouse_id.id,
            'date': date_scheduled,
            'date_deadline': False if self.group_propagation_option == 'fixed' else date_deadline,
            'propagate_cancel': self.propagate_cancel,
            'description_picking': picking_description,
            'priority': values.get('priority', "0"),
            'orderpoint_id': values.get('orderpoint_id') and values['orderpoint_id'].id,
            'product_packaging_id': values.get('product_packaging_id') and values['product_packaging_id'].id,
            'pkg_demand': values.get('pkg_demand'),
            'pkg_done': values.get('pkg_done'),
            'picking_type_id': values.get('picking_type_id'),
            # 'quantity_done':values.get('quantity_done'),
        }
        for field in self._get_custom_move_fields():
            if field in values:
                move_values[field] = values.get(field)
        return move_values


class AccountInvoiceLine(models.Model):
    _inherit = 'account.move.line'

    package_id = fields.Many2one('product.packaging')
    product_packaging_qty = fields.Float('Qty', default=1)
    pkg_unit_price = fields.Float()
    promo = fields.Selection([
        ('off', 'Price Off'),
        ('comp', 'Price Comp')], "Promotion")


    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_po_id
            self.quantity = 1.0
            self.product_packaging_qty = 1.0

    @api.onchange('package_id', 'product_packaging_qty')
    def _onchange_product_packaging_id(self):
        if self.package_id:
            self.quantity = self.package_id.qty * self.product_packaging_qty

    @api.onchange('pkg_unit_price')
    def _onchange_pkg_unit_price(self):
        if self.pkg_unit_price and self.package_id:
            self.price_unit = self.pkg_unit_price / self.package_id.qty
