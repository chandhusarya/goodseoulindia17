# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
from odoo.tools import float_repr, format_datetime


class ForecastProductPricelist(models.Model):
    _inherit = "product.pricelist"


    def _update_pricelist_promotion(self):
        #This method will update, all current data in the pricelist.

        #Off
        off_pricelist_items = self.env['product.pricelist.item'].search([('date_start', '!=', False), ('date_end', '!=', False), ('promo', '=', 'off')])
        off_aml_ids = []
        for pl in off_pricelist_items:
            moves = self.env['account.move.line'].search([('date', '>=', pl.date_start),('date', '<=', pl.date_end), ('partner_id', 'in', pl.pricelist_id.customer_ids.ids),
                                                          ('move_type', 'in', ['out_refund', 'out_invoice']), ('exclude_from_invoice_tab', '=', False), ('product_id', '=', pl.product_tmpl_id.product_variant_id.id),('promo','!=',True)])
            for move in moves:
                off_aml_ids.append(move.id)
        off_aml_ids = list(set(off_aml_ids))
        off_query = """UPDATE account_move_line SET promo = 'off' WHERE id in %s"""

        #COMPENSATION
        comp_pricelist_items = self.env['product.pricelist.item'].search([('date_start', '!=', False), ('date_end', '!=', False), ('promo', '=', 'comp')])
        comp_aml_ids = []
        for pl in comp_pricelist_items:
            moves = self.env['account.move.line'].search([('date', '>=', pl.date_start),('date', '<=', pl.date_end), ('partner_id', 'in', pl.pricelist_id.customer_ids.ids),
                                                          ('move_type', 'in', ['out_refund', 'out_invoice']), ('exclude_from_invoice_tab', '=', False), ('product_id', '=', pl.product_tmpl_id.product_variant_id.id),('promo','!=',True)])
            for move in moves:
                comp_aml_ids.append(move.id)
        comp_aml_ids = list(set(comp_aml_ids))
        comp_query = """UPDATE account_move_line SET promo = 'comp' WHERE id in %s"""

        self.env.cr.execute(off_query, (tuple(off_aml_ids),))
        self.env.cr.execute(comp_query, (tuple(comp_aml_ids),))
