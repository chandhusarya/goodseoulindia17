# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons import decimal_precision as dp
from datetime import datetime


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    pkg_unit_price = fields.Float("Pkg Unit Price")
    line_pkg_status = fields.Boolean(string="Line pkg status", default=False)

    package_received = fields.Float(string="Package Received", compute='_compute_package_received')
    package_billed = fields.Float(string="Package Billed", compute='_compute_package_billed')
    shipment_adv_qty = fields.Float(string="Shipment Advise Qty", compute='_compute_shipment_adv_qty', store=False)
    pending_qty_to_ship = fields.Float("Pending Qty to Ship", compute='_compute_pending_qty_to_ship')
    bl_qty = fields.Float(string="BL Qty", compute='_compute_bl_qty')

    def write(self, vals):
        # res = super(PurchaseOrderLine, self).write(vals)
        # Price Unit change
        if 'product_packaging_qty' in vals and vals['product_packaging_qty'] > 0:
            product_packaging_id = self.product_packaging_id
            if 'product_packaging_id' in vals:
                product_packaging_id = self.env['product.packaging'].browse([vals['product_packaging_id']])
            product_id = self.product_id
            if 'product_id' in vals:
                product_id = self.env['product.product'].browse([vals['product_id']])
            price_unit = 0
            supplier_info = self.env['product.supplierinfo'].search([('partner_id', '=', self.order_id.partner_id.id),
                                                                     ('product_tmpl_id', '=',
                                                                      product_id.product_tmpl_id.id),
                                                                     ('package_id', '=', product_packaging_id.id)],
                                                                    limit=1)
            if supplier_info:
                price_unit = supplier_info.package_price
            price_unit = price_unit / product_packaging_id.qty
            vals['price_unit'] = price_unit

        return super(PurchaseOrderLine, self).write(vals)

    def _compute_pending_qty_to_ship(self):
        for line in self:
            allocation = self.env['lpo.wise.shipment.allocation'].search([
                ('purchase_line_id', '=', line.id)])
            allocation_qty = 0
            for alloc in allocation:
                allocation_qty += alloc.shipment_advice_line_qty
            line.pending_qty_to_ship = line.product_packaging_qty - allocation_qty

    def _compute_shipment_adv_qty(self):
        for line in self:
            allocation = self.env['lpo.wise.shipment.allocation'].search([
                ('purchase_line_id', '=', line.id)])
            allocation_qty = 0
            for alloc in allocation:
                allocation_qty += alloc.shipment_advice_line_qty

            line.shipment_adv_qty = allocation_qty

    def _compute_package_received(self):
        for line in self:
            package = self.env['product.packaging'].search(
                [('product_id', '=', line.product_id.id), ('id', '=', line.product_packaging_id.id)])
            print(package)
            if line.qty_received != 0:
                line.package_received = line.qty_received / package.qty
            else:
                line.package_received = 0
            # moves = self.env['stock.move'].search([('sale_line_id', '=', line.id),('state','=','done')])
            # print(moves)
            # for data in moves:
            #     qty += data.pkg_done
            # self.package_received = qty

    def _compute_package_billed(self):
        for line in self:
            package = self.env['product.packaging'].search(
                [('product_id', '=', line.product_id.id), ('id', '=', line.product_packaging_id.id)])
            print(package)
            if line.qty_invoiced != 0:
                line.package_billed = line.qty_invoiced / package.qty
            else:
                line.package_billed = 0
            # bills = self.env['account.move.line'].search([('purchase_line_id', '=', line.id),('parent_state','=','posted')])
            # line.product_id.packaging_ids
            # print(bills)
            # for data in bills:
            #     qty += data.product_packaging_qty
            # self.package_billed = qty

    @api.onchange('product_id', 'product_qty', 'product_uom')
    def _onchange_suggest_packaging(self):
        # remove packaging if not match the product
        if self.product_packaging_id.product_id != self.product_id:
            self.product_packaging_id = False

    @api.onchange('product_packaging_id')
    def _onchange_product_packaging_id(self):
        for rec in self:
            if rec.product_packaging_id and rec.product_qty:
                newqty = self.product_packaging_id._check_qty(self.product_qty, self.product_uom, "UP")

    @api.onchange('pkg_unit_price')
    def _onchange_pkg_unit_price(self):
        for rec in self:
            if rec.pkg_unit_price and rec.product_packaging_id:
                  rec.price_unit = rec.pkg_unit_price / rec.product_packaging_id.qty

    @api.constrains('pkg_unit_price')
    def _check_pkg_unit_price(self):
        for rec in self:
            if rec.pkg_unit_price == 0.00:
                raise ValidationError(_("Package unit Price can not be null"))

    @api.onchange('product_packaging_id')
    def _onchange_update_product_packaging_qty(self):
        if not self.product_packaging_id:
            self.product_packaging_qty = 0
        else:
            packaging_uom = self.product_packaging_id.product_uom_id
            packaging_uom_qty = self.product_uom._compute_quantity(self.product_qty, packaging_uom)

            name = ""
            if self.product_packaging_id.description:
                name = self.product_packaging_id.description
            else:
                name = self.product_packaging_id.product_id.name

            self.name = name
            self.product_packaging_qty = 1
            self.product_qty = self.product_packaging_qty * self.product_packaging_id.qty


            #Update price unit

            price_unit = 0
            supplier_info = self.env['product.supplierinfo'].search([('partner_id', '=', self.order_id.partner_id.id),
                                                                     ('product_tmpl_id', '=',  self.product_id.product_tmpl_id.id),
                                                                     ('package_id', '=', self.product_packaging_id.id),
                                                                     ('company_id', '=', self.order_id.company_id.id)],
                                                                    limit=1)

            if supplier_info:
                price_unit = supplier_info.package_price
            self.pkg_unit_price = price_unit
            price_unit = price_unit / self.product_packaging_id.qty
            self.write({'price_unit': price_unit})




    def _prepare_account_move_line(self, move=False):
        """overrided to include package details in purchase order line"""
        self.ensure_one()
        aml_currency = move and move.currency_id or self.currency_id
        date = move and move.date or fields.Date.today()

        res = {
            'display_type': self.display_type,
            'sequence': self.sequence,
            'name': '%s: %s' % (self.order_id.name, self.name),
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'quantity': self.qty_to_invoice,
            'price_unit': self.currency_id._convert(self.price_unit, aml_currency, self.company_id, date, round=False),
            'tax_ids': [(6, 0, self.taxes_id.ids)],
            #'analytic_account_id': self.account_analytic_id.id,
            #'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
            'purchase_line_id': self.id,
            'package_id': self.product_packaging_id.id,
            'product_packaging_qty': self.product_packaging_qty,
            'pkg_unit_price': self.pkg_unit_price,
        }
        if not move:
            return res

        if self.currency_id == move.company_id.currency_id:
            currency = False
        else:
            currency = move.currency_id

        res.update({
            'move_id': move.id,
            'currency_id': currency and currency.id or False,
            'date_maturity': move.invoice_date_due,
            'partner_id': move.partner_id.id,
        })
        return res

    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        """Override original function"""
        self.ensure_one()
        self._check_orderpoint_picking_type()
        product = self.product_id.with_context(lang=self.order_id.dest_address_id.lang or self.env.user.lang)
        date_planned = self.date_planned or self.order_id.date_planned
        return {
            # truncate to 2000 to avoid triggering index limit error
            # TODO: remove index in master?
            'name': (self.name or '')[:2000],
            'product_id': self.product_id.id,
            'date': date_planned,
            'date_deadline': date_planned,
            'location_id': self.order_id.partner_id.property_stock_supplier.id,
            'location_dest_id': (self.orderpoint_id and not (
                    self.move_ids | self.move_dest_ids)) and self.orderpoint_id.location_id.id or self.order_id._get_destination_location(),
            'picking_id': picking.id,
            'partner_id': self.order_id.dest_address_id.id,
            'move_dest_ids': [(4, x) for x in self.move_dest_ids.ids],
            'state': 'draft',
            'purchase_line_id': self.id,
            'company_id': self.order_id.company_id.id,
            'price_unit': price_unit,
            'picking_type_id': self.order_id.picking_type_id.id,
            'group_id': self.order_id.group_id.id,
            'origin': self.order_id.name,
            'description_picking': product.description_pickingin or self.name,
            'propagate_cancel': self.propagate_cancel,
            'warehouse_id': self.order_id.picking_type_id.warehouse_id.id,
            'product_uom_qty': product_uom_qty,
            'product_uom': product_uom.id,
            'product_packaging_id': self.product_packaging_id.id,
            'pkg_demand': self.product_packaging_qty if self.product_packaging_qty else '',
        }

    @api.onchange('product_qty', 'product_uom')
    def _onchange_quantity(self):
        """ Override original function to not calculate unit price from pricelist again"""
        return



class StockMove(models.Model):
    _inherit = 'stock.move'

    pkg_demand = fields.Float()
    pkg_done = fields.Float('Done(pkg)')
    lot_name = fields.Char()

    primary_packaging_id = fields.Many2one('product.packaging', 'Primary Package', compute='_find_primary_package')



    def write(self, values):
        res = super(StockMove, self).write(values)

        print("\n\n\n\n\n\nvalues ==========>> ", values)
        for move in self:
            if move.picking_type_id.code == 'outgoing' and move.date.date() > datetime(2025, 7, 1).date():
                primary_packaging = ""
                if move.primary_packaging_id:
                    primary_packaging = move.primary_packaging_id.name
                demand_qty = move.product_uom_qty
                total_move_line_qty = 0
                for mv_line in move.move_line_ids:
                    total_move_line_qty += mv_line.quantity

                if round(total_move_line_qty, 2) > round(demand_qty, 2):
                    raise UserError(_("You cannot add more than the demand qty for item %s. Demand Demand is : %s %s, Qty you selected is : %s %s" % (move.product_id.name, str(demand_qty), primary_packaging, str(total_move_line_qty), primary_packaging)))

        return res










    def _find_primary_package(self):
        for move in self:
            primary_packaging_id = False
            for pack in move.product_id.packaging_ids:
                if pack.primary_unit:
                    primary_packaging_id = pack.id
            move.primary_packaging_id = primary_packaging_id

    @api.constrains('pkg_done')
    def _check_description(self):
        for record in self:
            if record.pkg_done > record.pkg_demand:
                raise ValidationError("Done quantity should not be greater than demand quantity")

    @api.onchange('pkg_done')
    def _onchange_pkg_done(self):
        for rec in self:
            if rec.pkg_done > rec.pkg_demand:
                raise ValidationError(_("Done quantity should not be greated than demand quantity"))
            else:
                packaging_uom = self.product_packaging_id.product_uom_id
                packaging_uom_qty = self.product_uom._compute_quantity(self.pkg_done, packaging_uom)
                self.quantity_done = packaging_uom_qty * self.product_packaging_id.qty


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    primary_packaging_id = fields.Many2one('product.packaging', 'Primary Package', compute='_find_primary_package')

    def _find_primary_package(self):
        for move in self:
            primary_packaging_id = False
            for pack in move.product_id.packaging_ids:
                if pack.primary_unit:
                    primary_packaging_id = pack.id
            move.primary_packaging_id = primary_packaging_id