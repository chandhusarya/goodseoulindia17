
# -*- coding: utf-8 -*-
import datetime

from odoo import models, fields, api,_
import logging
_logger = logging.getLogger(__name__)


class SalesBudgetImportTemplate(models.AbstractModel):
    _name = 'report.sry_forecast_analysis.budget_import_template'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, lines):
        violet_header_format = workbook.add_format({'font_size': 10, 'align': 'vcenter', 'bg_color': '#D9E1F2','font_color':'#0000FF', 'bold': True, 'border': True})

        cell_format_lock = workbook.add_format({'border': 1})
        cell_format_unlock = workbook.add_format({'border': 1, 'locked': False})
        data_sheet = workbook.add_worksheet('Template')
        data_sheet.freeze_panes(1, 0)

        customers = self.env['master.parent'].search([])#.mapped('master_parent_id')
        products = self.env['product.product'].search([('active', '=', 'True'), ('type', '=', 'product')])

        #DATASHEET
        data_sheet.set_column(0, 0, 0)  #masterparent_id
        data_sheet.set_column(1, 1, 30) #masterparent name
        data_sheet.set_column(2, 2, 0)  #product_id
        data_sheet.set_column(3, 3, 15) #Item Code
        data_sheet.set_column(4, 4, 60) #Description
        data_sheet.set_column(5, 5, 14) #Category

        # Data 1st line header
        data_sheet.write(0, 0, "master_parent_id", violet_header_format)
        data_sheet.write(0, 1, "Master Parent", violet_header_format)
        data_sheet.write(0, 2, "product_id", violet_header_format)
        data_sheet.write(0, 3, "Item Code", violet_header_format)
        data_sheet.write(0, 4, "Description", violet_header_format)
        data_sheet.write(0, 5, "Category", violet_header_format)
        data_sheet.write(0, 6, "Quantity", violet_header_format)

        data_row = 1
        for customer in customers:
            for product in products:
                data_sheet.write(data_row, 0, customer.id, cell_format_lock)
                data_sheet.write(data_row, 1, customer.name, cell_format_lock)
                data_sheet.write(data_row, 2, product.id, cell_format_lock)
                data_sheet.write(data_row, 3, product.default_code, cell_format_lock)
                data_sheet.write(data_row, 4, product.name, cell_format_lock)
                data_sheet.write(data_row, 5, product.categ_id.name, cell_format_lock)
                data_sheet.write(data_row, 6, '', cell_format_unlock)
                data_row += 1

        data_sheet.autofilter(0, 1, 0, 6)
        data_sheet.protect(password='sarya',  options={'autofilter': True, 'delete_rows': True})