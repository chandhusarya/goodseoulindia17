# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo import tools


class ShipmentAdviceETAReport(models.Model):
    _name = "shipment.advice.eta.report"
    _auto = False

    departure_date = fields.Date('ETD')
    expected_date = fields.Date('ETA')
    product_id = fields.Many2one('product.product', 'Product')
    product_packaging_id = fields.Many2one('product.packaging', string='UOM')
    expiry_date = fields.Date("Expiry Date")
    qty_to_receive = fields.Float("Qty to Receive")
    bl_entry_id = fields.Many2one('bl.entry', string='Bl Entry')
    state = fields.Selection(
        string='Status',
        selection=[
            ('draft', 'Draft'),
            ('waiting_finance_approval', 'Waiting Finance Approval'),
            ('finance_approved', 'Finance Approved'),
            ('inspection', 'Inspection'),
            ('open', 'Open'),
            ('done', 'Close'),
            ('item_in_receiving', 'Item in Inspection Location'),
            ('item_received', 'Received'),
            ('cancel', 'Cancelled'),
        ])

    packaging = fields.Char("Packaging")


    def init(self):
        rs = self._cr.execute("""
        CREATE OR REPLACE VIEW shipment_advice_eta_report AS (

            SELECT row_number() OVER () as id,
            bl_e.departure_date as departure_date,
            bl_e.expected_date as expected_date,
            bl_l.product_id as product_id,
            bl_l.product_packaging_id as product_packaging_id,
            bl_d.expiry_date as expiry_date, 
            bl_d.qty_to_receive as qty_to_receive,
            bl_l.bl_entry_id as bl_entry_id,
            sa.state as state,
            prd_p.name as packaging
            
            from bl_entry_lines_details as bl_d
            JOIN bl_entry_lines bl_l ON bl_d.bl_entry_line_id = bl_l.id
            JOIN bl_entry bl_e ON bl_l.bl_entry_id = bl_e.id
            JOIN product_packaging as prd_p ON bl_l.product_packaging_id = prd_p.id
            LEFT JOIN shipment_advice sa ON bl_l.container_id = sa.bl_entry_container_id
            
            WHERE sa.state != 'item_received' OR sa.state IS NULL
        
        ) """)
