# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo import tools

class InventoryReportCTN(models.Model):
    _name = "inventory.report.ctn"
    _auto = False

    product_id = fields.Many2one('product.product', string='Product')
    location_id = fields.Many2one('stock.location', string='Location')
    lot_id = fields.Many2one('stock.lot', 'Lot/Serial Number')
    quantity = fields.Float(string='Product Qty')
    reserved_quantity = fields.Float(string='Reserved Qty')
    pcp = fields.Float(string='PCP')
    ctn_qty = fields.Float(string='Qty in CTN')
    ctn_reserved = fields.Float(string='Reserved Qty in CTN')



    def init(self):
       rs=self._cr.execute("""
        CREATE OR REPLACE VIEW inventory_report_ctn AS (
            SELECT
                sq.id,
                sq.product_id,
                sq.location_id,
                sq.lot_id,
                sq.quantity,
                sq.reserved_quantity,
                MAX(pp.qty) AS pcp,
                sq.quantity / MAX(pp.qty) AS ctn_qty,
                sq.reserved_quantity / MAX(pp.qty) AS ctn_reserved
            FROM
                stock_quant sq
            LEFT JOIN
                stock_location location ON location.id = sq.location_id
            JOIN
                product_product prd ON prd.id = sq.product_id
            LEFT JOIN
                product_packaging pp ON sq.product_id = pp.product_id
            WHERE
                location.usage = 'internal'
                AND sq.quantity != 0
            GROUP BY
                sq.id,
                sq.product_id,
                prd.product_tmpl_id,
                sq.location_id,
                sq.lot_id,
                sq.quantity,
                sq.reserved_quantity
        )""")



