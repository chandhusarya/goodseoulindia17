# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
import logging
import time
from datetime import timedelta,datetime

_logger = logging.getLogger(__name__)

class SryYTDReportFilterWizard(models.TransientModel):
    _name = "sry.ytd.report.filter.wizard"
    _description = "Route YTD Report Filter Wizard"


    date = fields.Date('Date')
    date_criteria = fields.Selection([
                                        ('last30', 'Last 30 Days'),
                                        ('prevmonth', 'Previous Month'),
                                        ('thismonth', 'This Month'),
                                        ('prevyear', 'Previous Year'),
                                        ('thisyear', 'This Year'),
                                        ('prevthisyr', 'Previous & This Year'),
                                        ('range', 'Date Range'),
                                        ], string='Criteria', required=True, default='prevthisyr')

    from_date = fields.Date('Date From: ')
    to_date = fields.Date('Date To: ')

    raw_data = fields.Boolean('YTD Data')
    prof_raw_data = fields.Boolean('Profitability Data')
    trade_channel = fields.Boolean('Trade Channel')
    brand_trade_channel = fields.Boolean('Brand-Trade Channel')
    brand_customer_group = fields.Boolean('Brand-Customer Group')
    brand_sku_wise = fields.Boolean('Brand-SKU Wise')
    daily_sales_value = fields.Boolean('Daily Sales Value')
    kam_brand_sku = fields.Boolean('KAM-Brand-SKU')
    van_sm_bw_sales = fields.Boolean('Van Salesman BW Sales')
    manager_wise = fields.Boolean('Manager Wise')

    def get_search_domain(self):
        search_domain_view = []
        date_start = ''
        date_end = ''

        if self.date_criteria == 'last30':
            date_start = fields.date.today() - timedelta(days=29)
            date_end = fields.date.today()
        elif self.date_criteria == 'thismonth':
            date_start = fields.date.today().replace(day=1)
            date_end = fields.date.today()
        elif self.date_criteria == 'prevmonth':
            date_start = date_end.replace(day=1)
            date_end = fields.date.today().replace(day=1) - timedelta(days=1)
        elif self.date_criteria == 'prevyear':
            date_start = fields.date.today().replace(day=1, month=1, year=fields.date.today().year - 1)
            date_end = fields.date.today().replace(day=1, month=1) - timedelta(days=1)
        elif self.date_criteria == 'thisyear':
            date_start = fields.date.today().replace(day=1, month=1)
            date_end = fields.date.today()
        elif self.date_criteria == 'prevthisyr':
            date_start = fields.date.today().replace(day=1, month=1, year=fields.date.today().year - 1)
            date_end = fields.date.today()
        elif self.date_criteria == 'range':
            date_start = self.from_date
            date_end = self.to_date
        elif self.date_criteria == 'ondate':
            date_end = date_start = self.date

        if not date_start or not date_end:
            date_start = '2021-12-31'
            date_end = datetime.now().strftime('%Y-%m-%d')
        else:
            search_domain_view.append(('date', '>=', date_start))
            search_domain_view.append(('date', '<=', date_end))
        return date_start, date_end

    def button_generate_xlsx(self):
        date_start, date_end = self.get_search_domain()
        data = {}
        data['date_start'] = date_start
        data['date_end'] = date_end
        report = []

        if self.trade_channel: report.append('trade_channel')
        if self.brand_trade_channel: report.append('brand_trade_channel')
        if self.brand_customer_group: report.append('brand_customer_group')
        if self.brand_sku_wise: report.append('brand_sku_wise')
        if self.daily_sales_value: report.append('daily_sales_value')
        if self.kam_brand_sku: report.append('kam_brand_sku')
        if self.van_sm_bw_sales: report.append('van_sm_bw_sales')
        if self.manager_wise: report.append('manager_wise')
        if self.raw_data: report.append('raw_ytd_data')
        if self.prof_raw_data: report.append('raw_prof_data')

        data['req_reports'] = report
        return self.env.ref('sry_forecast_analysis.ytd_report').report_action(self, data=data)

class SaryaYTDReport(models.AbstractModel):
    _name = 'report.sry_forecast_analysis.ytd_report'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, lines):
        date_start = data['date_start']
        date_end = data['date_end']
        req_reports = data['req_reports']
        duration_data = []

        if 'raw_prof_data' in req_reports:
            prof_rawdata, duration_detail = self._get_profitability_rawdata(date_start, date_end)
            duration_data.append(duration_detail)
        else:
            ytd_rawdata, duration_detail = self._get_ytd_rawdata(date_start, date_end)
            duration_data.append(duration_detail)

        if 'trade_channel' in req_reports:
            duration_detail = self._create_tradechannel_sheet(workbook, ytd_rawdata)
            duration_data.append(duration_detail)

        if 'brand_trade_channel' in req_reports:
            duration_detail = self._create_brand_tradechannel_sheet(workbook, ytd_rawdata)
            duration_data.append(duration_detail)

        if 'brand_customer_group' in req_reports:
            duration_detail = self._create_brand_customergroup_sheet(workbook, ytd_rawdata)
            duration_data.append(duration_detail)

        if 'brand_sku_wise' in req_reports:
            duration_detail = self._create_brand_skuwise_sheet(workbook, ytd_rawdata)
            duration_data.append(duration_detail)

        if 'daily_sales_value' in req_reports:
            duration_detail =  self._create_daily_sales_value_sheet(workbook, ytd_rawdata)
            duration_data.append(duration_detail)

        if 'kam_brand_sku' in req_reports:
            duration_detail = self._create_kam_brand_sku_sheet(workbook, ytd_rawdata)
            duration_data.append(duration_detail)

        if 'van_sm_bw_sales' in req_reports:
            duration_detail  = self._create_vansalesman_bw_sales_sheet(workbook, ytd_rawdata)
            duration_data.append(duration_detail)

        if 'manager_wise' in req_reports:
            duration_detail = self._create_managers_sales(workbook, ytd_rawdata)
            duration_data.append(duration_detail)

        if 'raw_ytd_data' in req_reports:
            duration_detail = self._create_ytd_rawdata_sheet(workbook, ytd_rawdata)
            duration_data.append(duration_detail)

        if 'raw_prof_data' in req_reports:
            duration_detail = self._create_profitability_rawdata_sheet(workbook, prof_rawdata)
            duration_data.append(duration_detail)

        self._create_query_details(workbook, duration_data, date_start, date_end)

    def _create_managers_sales(self,workbook,rawdata):
        start_time = time.time()
        BLU1_CNT = workbook.add_format({'bg_color': '#4D93D9', 'align': 'center', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1})
        BLU2_LFT = workbook.add_format({'bg_color': '#78ADE2', 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue'})
        BLU2_NUM = workbook.add_format({'bg_color': '#78ADE2', 'align': 'right', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue', 'num_format': '#,##0.00'})
        BLU3_NUM = workbook.add_format({'bg_color': '#B3D1EF', 'align': 'right', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue', 'num_format': '#,##0.00'})
        BLU3_LFT = workbook.add_format({'bg_color': '#B3D1EF', 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue'})
        BLU4_NUM = workbook.add_format({'bg_color': '#DAE9F8', 'align': 'right', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue', 'num_format': '#,##0.00'})
        BLU4_LFT = workbook.add_format({'bg_color': '#DAE9F8', 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue'})

        NORM_LFT = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'border': 1, 'border_color':'blue'})
        NORM_NUM = workbook.add_format({'align': 'right', 'valign': 'vcenter', 'border': 1, 'num_format': '#,##0.00', 'border_color':'blue'})

        periods = sorted(set([data['date'].strftime('%Y-%m') for data in rawdata]))
        years = sorted(set([data['date'].strftime('%Y') for data in rawdata]))
        managers = sorted(set([data['account_manager'] for data in rawdata if data['account_manager']]))
        for manager in managers:
            sheet = workbook.add_worksheet(manager)

            #HEADER PART
            sheet.merge_range(0, 0, 2, 0, 'Account Manager', BLU1_CNT)
            sheet.set_column(0, 0, 15)
            sheet.merge_range(0, 1, 2, 1, 'Master Parent', BLU1_CNT)
            sheet.set_column(1, 1, 20)
            sheet.merge_range(0, 2, 2, 2, 'Delivery Address', BLU1_CNT)
            sheet.set_column(2, 2, 15)
            sheet.merge_range(0, 3, 2, 3, 'Brand Name', BLU1_CNT)
            sheet.set_column(3, 3, 15)
            sheet.merge_range(0, 4, 2, 4, 'Product Category', BLU1_CNT)
            sheet.set_column(4, 4, 30)
            sheet.merge_range(0, 5, 2, 5, 'Item Description', BLU1_CNT)
            sheet.set_column(5, 5, 30)
            colnum = 6
            for year in years:
                year_period = sorted(set([period for period in periods if datetime.strptime(period, '%Y-%m').strftime('%Y') == year])) #Variable created to check the number of months on same year
                year_mon = [datetime.strptime(period, '%Y-%m').strftime('%b') for period in periods if datetime.strptime(period, '%Y-%m').strftime('%Y') == year]
                yr_end_col = colnum - 1 + (len(year_period) * 2)
                sheet.set_column(colnum, yr_end_col, 15)
                sheet.write(0, colnum, year, BLU1_CNT) if colnum == yr_end_col else sheet.merge_range(0, colnum, 0, yr_end_col, year, BLU1_CNT)
                for mon in year_mon:
                    sheet.merge_range(1, colnum, 1, colnum + 1, mon, BLU1_CNT)
                    sheet.write(2, colnum, 'Qty in CTN', BLU1_CNT)
                    sheet.write(2, colnum + 1, 'Sales', BLU1_CNT)
                    colnum += 2
                sheet.set_column(colnum, colnum + 1, 15)
                sheet.merge_range(0, colnum, 2, colnum, str(year) + ' Total QTY in CTN', BLU1_CNT)
                sheet.merge_range(0, colnum + 1 , 2, colnum +1 , str(year) + ' Total Sales', BLU1_CNT)
                colnum += 2
            sheet.set_column(colnum, colnum + 1, 20)
            sheet.merge_range(0 ,colnum, 2, colnum, 'Grand Total Qty in CTN', BLU1_CNT)
            sheet.merge_range(0 ,colnum + 1, 2, colnum + 1, 'Grand Total Sales', BLU1_CNT)

            #DETAIL PART
            rownum = 3
            overall_total = {}
            masters = sorted(set([data['master_parent'] for data in rawdata if data['master_parent'] and data['account_manager'] == manager]))
            for master in masters:
                delivery_addresses = sorted(set([data['delivery_address'] for data in rawdata if data['delivery_address'] and data['account_manager'] == manager and data['master_parent'] == master]))
                master_totals = {}
                for address in delivery_addresses:
                    brands = sorted(set([data['brand'] for data in rawdata if data['brand'] and data['delivery_address'] == address and data['account_manager']]))
                    address_totals = {}
                    for brand in brands:
                        categories = sorted(set([data['product_category'] for data in rawdata if data['product_category'] and data['brand'] == brand
                                                 and data['delivery_address'] == address and data['master_parent'] == master and data['account_manager']]))
                        brand_totals = {}
                        for category in categories:
                            products = sorted(set([data['product'] for data in rawdata if data['product_category'] and data['brand'] == brand
                                                 and data['delivery_address'] == address and data['master_parent'] == master and data['account_manager']]))
                            category_totals = {}
                            for product in products:
                                line_total_sales = 0
                                line_total_qty = 0
                                sheet.write(rownum, 0, manager, NORM_LFT)
                                sheet.write(rownum, 1, master, NORM_LFT)
                                sheet.write(rownum, 2, address, NORM_LFT)
                                sheet.write(rownum, 3, brand, NORM_LFT)
                                sheet.write(rownum, 4, category, NORM_LFT)
                                sheet.write(rownum, 5, product, NORM_LFT)
                                colnum = 6
                                for year in years:
                                    year_total_sales = 0
                                    year_total_qty = 0
                                    month_nos = [datetime.strptime(period, '%Y-%m').strftime('%m') for period in periods if period.startswith(year)]
                                    for month_no in month_nos:
                                        ctn_qty = sum([data['quantity_ctn'] for data in rawdata
                                                           if data['quantity_ctn']
                                                           and data['account_manager'] == manager
                                                           and data['master_parent'] == master
                                                           and data['delivery_address'] == address
                                                           and data['brand'] == brand
                                                           and data['product_category'] == category
                                                           and data['product'] == product
                                                           and data['date'].strftime('%Y') == year
                                                           and data['date'].strftime('%m') == month_no])
                                        sheet.write(rownum, colnum, ctn_qty if ctn_qty else '', NORM_NUM)
                                        category_totals[colnum] = (category_totals[colnum] + ctn_qty) if category_totals and colnum in category_totals else ctn_qty
                                        brand_totals[colnum] = (brand_totals[colnum] + ctn_qty) if brand_totals and colnum in brand_totals else ctn_qty
                                        address_totals[colnum] = (address_totals[colnum] + ctn_qty) if address_totals and colnum in address_totals else ctn_qty
                                        master_totals[colnum] = (master_totals[colnum] + ctn_qty) if master_totals and colnum in master_totals else ctn_qty
                                        overall_total[colnum] = (overall_total[colnum] + ctn_qty) if overall_total and colnum in overall_total else ctn_qty
                                        colnum += 1
                                        year_total_qty += ctn_qty
                                        sales_value = sum([data['sales_value'] for data in rawdata
                                                           if data['account_manager'] == manager
                                                           and data['master_parent'] == master
                                                           and data['delivery_address'] == address
                                                           and data['brand'] == brand
                                                           and data['product_category'] == category
                                                           and data['product'] == product
                                                           and data['date'].strftime('%Y') == year
                                                           and data['date'].strftime('%m') == month_no])
                                        sheet.write(rownum, colnum, sales_value if sales_value else '', NORM_NUM)
                                        category_totals[colnum] = (category_totals[colnum] + sales_value) if category_totals and colnum in category_totals else sales_value
                                        brand_totals[colnum] = (brand_totals[colnum] + sales_value) if brand_totals and colnum in brand_totals else sales_value
                                        address_totals[colnum] = (address_totals[colnum] + sales_value) if address_totals and colnum in address_totals else sales_value
                                        master_totals[colnum] = (master_totals[colnum] + sales_value) if master_totals and colnum in master_totals else sales_value
                                        overall_total[colnum] = (overall_total[colnum] + sales_value) if overall_total and colnum in overall_total else sales_value
                                        colnum += 1
                                        year_total_sales += sales_value
                                    # Year Total Qty
                                    sheet.write(rownum, colnum, year_total_qty if year_total_qty else '', NORM_NUM)
                                    category_totals[colnum] = (category_totals[colnum] + year_total_qty) if category_totals and colnum in category_totals else year_total_qty
                                    brand_totals[colnum] = (brand_totals[colnum] + year_total_qty) if brand_totals and colnum in brand_totals else year_total_qty
                                    address_totals[colnum] = (address_totals[colnum] + year_total_qty) if address_totals and colnum in address_totals else year_total_qty
                                    master_totals[colnum] = (master_totals[colnum] + year_total_qty) if master_totals and colnum in master_totals else year_total_qty
                                    overall_total[colnum] = (overall_total[colnum] + year_total_qty) if overall_total and colnum in overall_total else year_total_qty
                                    colnum += 1
                                    #Year Total Sales
                                    sheet.write(rownum, colnum, year_total_sales if year_total_sales else '', NORM_NUM)
                                    category_totals[colnum] = (category_totals[colnum] + year_total_sales) if category_totals and colnum in category_totals else year_total_sales
                                    brand_totals[colnum] = (brand_totals[colnum] + year_total_sales) if brand_totals and colnum in brand_totals else year_total_sales
                                    address_totals[colnum] = (address_totals[colnum] + year_total_sales) if address_totals and colnum in address_totals else year_total_sales
                                    master_totals[colnum] = (master_totals[colnum] + year_total_sales) if master_totals and colnum in master_totals else year_total_sales
                                    overall_total[colnum] = (overall_total[colnum] + year_total_sales) if overall_total and colnum in overall_total else year_total_sales
                                    colnum += 1
                                # Line Total Qty
                                sheet.write(rownum, colnum, line_total_qty if line_total_qty else '', NORM_NUM)
                                category_totals[colnum] = (category_totals[colnum] + line_total_qty) if category_totals and colnum in category_totals else line_total_qty
                                brand_totals[colnum] = (brand_totals[colnum] + line_total_qty) if brand_totals and colnum in brand_totals else line_total_qty
                                address_totals[colnum] = (address_totals[colnum] + line_total_qty) if address_totals and colnum in address_totals else line_total_qty
                                master_totals[colnum] = (master_totals[colnum] + line_total_qty) if master_totals and colnum in master_totals else line_total_qty
                                overall_total[colnum] = (overall_total[colnum] + line_total_qty) if overall_total and colnum in overall_total else line_total_qty
                                colnum += 1
                                #Line Total Sales
                                sheet.write(rownum, colnum, line_total_sales if line_total_sales else '', NORM_NUM)
                                category_totals[colnum] = (category_totals[colnum] + line_total_sales) if category_totals and colnum in category_totals else line_total_sales
                                brand_totals[colnum] = (brand_totals[colnum] + line_total_sales) if brand_totals and colnum in brand_totals else line_total_sales
                                address_totals[colnum] = (address_totals[colnum] + line_total_sales) if address_totals and colnum in address_totals else line_total_sales
                                master_totals[colnum] = (master_totals[colnum] + line_total_sales) if master_totals and colnum in master_totals else line_total_sales
                                overall_total[colnum] = (overall_total[colnum] + line_total_sales) if overall_total and colnum in overall_total else line_total_sales
                                rownum += 1
                            # Category Totals
                            sheet.write(rownum, 0, manager, NORM_LFT)
                            sheet.write(rownum, 1, master, NORM_LFT)
                            sheet.write(rownum, 2, address, NORM_LFT)
                            sheet.write(rownum, 3, brand, NORM_LFT)
                            sheet.write(rownum, 4, str(category) + ' Totals', NORM_LFT)
                            for col in range(5, colnum + 1):
                                sheet.write(rownum, col, category_totals.get(col) if category_totals.get(col) else '', NORM_NUM)
                            rownum += 1
                        # Brand Totals
                        sheet.write(rownum, 0, manager, NORM_LFT)
                        sheet.write(rownum, 1, master, NORM_LFT)
                        sheet.write(rownum, 2, address, NORM_LFT)
                        sheet.write(rownum, 3, str(brand) + ' Totals', NORM_LFT)
                        for col in range(4, colnum + 1):
                            sheet.write(rownum, col, brand_totals.get(col) if brand_totals.get(col) else '', NORM_NUM)
                        rownum += 1
                    # Delivery Address Totals
                    sheet.write(rownum, 0, manager, NORM_LFT)
                    sheet.write(rownum, 1, master, NORM_LFT)
                    sheet.write(rownum, 2, str(address), NORM_LFT)
                    for col in range(3, colnum + 1):
                        sheet.write(rownum, col, address_totals.get(col) if address_totals.get(col) else '', NORM_NUM)
                    rownum += 1
                # Master Parent Address Totals
                sheet.write(rownum, 0, manager, NORM_LFT)
                sheet.write(rownum, 1, str(master), NORM_LFT)
                for col in range(2, colnum + 1):
                    sheet.write(rownum, col, master_totals.get(col) if master_totals.get(col) else '', NORM_NUM)
                rownum += 1
            # Overall Totals
            sheet.write(rownum, 0, 'Grand Total', NORM_LFT)
            for col in range(1, colnum + 1):
                sheet.write(rownum, col, overall_total.get(col) if overall_total.get(col) else '', NORM_LFT)
            rownum += 1
        end_time = time.time()
        duration_detail = {'description' : 'Account Manager Sheet',
                           'time_taken' : end_time - start_time}
        return duration_detail

    def _create_vansalesman_bw_sales_sheet(self, workbook, rawdata):
        start_time = time.time()
        sheet = workbook.add_worksheet('Van Salesman BW Sales')
        BLU1_CNT = workbook.add_format({'bg_color': '#4D93D9', 'align': 'center', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1})
        BLU4_LFT = workbook.add_format({'bg_color': '#DAE9F8', 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue'})
        BLU2_NUM = workbook.add_format({'bg_color': '#78ADE2', 'align': 'right', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue', 'num_format': '#,##0.00'})
        BLU3_NUM = workbook.add_format({'bg_color': '#B3D1EF', 'align': 'right', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue', 'num_format': '#,##0.00'})
        BLU3_LFT = workbook.add_format({'bg_color': '#B3D1EF', 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue'})
        BLU4_NUM = workbook.add_format({'bg_color': '#DAE9F8', 'align': 'right', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue', 'num_format': '#,##0.00'})

        NORM_LFT = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'border': 1, 'border_color':'blue'})
        NORM_NUM = workbook.add_format({'align': 'right', 'valign': 'vcenter', 'border': 1, 'num_format': '#,##0.00', 'border_color':'blue'})

        sheet.merge_range(0, 0, 2, 0, 'Sub Classification', BLU1_CNT)
        sheet.set_column(0, 0, 15)
        sheet.merge_range(0, 1, 2, 1, 'Salesman', BLU1_CNT)
        sheet.set_column(1, 1, 20)


        periods = sorted(set([data['date'].strftime('%Y-%m') for data in rawdata]))
        years = sorted(set([data['date'].strftime('%Y') for data in rawdata]))

        #####BRAND WISE REPORT
        #Header Part
        colnum = 2
        brands = sorted(set([data['brand'] for data in rawdata if data['brand']]))
        for brand in brands:
            brand_end_col = colnum + len(years) + len(periods)
            sheet.merge_range(0, colnum, 0, brand_end_col, brand, BLU1_CNT)
            for year in years:
                year_period = sorted(set([period for period in periods if datetime.strptime(period, '%Y-%m').strftime('%Y') == year])) #Variable created to check the number of months on same year
                year_mon = [datetime.strptime(period, '%Y-%m').strftime('%b') for period in periods if datetime.strptime(period, '%Y-%m').strftime('%Y') == year]
                yr_end_col = colnum + len(year_period)
                sheet.write(1, colnum, year, BLU1_CNT) if colnum == yr_end_col else sheet.merge_range(1, colnum, 1, yr_end_col, year, BLU1_CNT)
                for mon in year_mon:
                    sheet.write(2, colnum, mon, BLU1_CNT)
                    colnum += 1
                sheet.write(2, colnum, str(year) + ' Total', BLU1_CNT)
                colnum += 1
            sheet.merge_range(1, colnum, 2, colnum, str(brand) + ' Total', BLU1_CNT)
            colnum += 1
        sheet.merge_range(0, colnum, 2, colnum, 'Grand Total', BLU1_CNT)
        colnum += 1

        #Detail Part
        rownum = 3
        overall_total = {}
        sub_classes = sorted(set([data['customer_sub_classification'] for data in rawdata if data['customer_sub_classification'] and data['account_manager'] == 'Tom']))
        for sub_class in sub_classes:
            salesmen = sorted(set([data['van_salesman'] for data in rawdata if data['van_salesman'] and data['customer_sub_classification'] == sub_class]))
            sub_class_totals = {}
            for salesman in salesmen:
                sheet.write(rownum, 0, sub_class, NORM_LFT)
                sheet.write(rownum, 1, salesman, NORM_LFT)
                colnum = 2
                line_total = 0
                for brand in brands:
                    brand_total = 0
                    for year in years:
                        year_total = 0
                        month_nos = [datetime.strptime(period, '%Y-%m').strftime('%m') for period in periods if period.startswith(year)]
                        for month_no in month_nos:
                            sales_value = sum([data['sales_value'] for data in rawdata
                                if data['customer_sub_classification'] == sub_class
                                and data['van_salesman'] == salesman
                                and data['brand'] == brand
                                and data['date'].strftime('%Y') == year
                                and data['date'].strftime('%m') == month_no])
                            sheet.write(rownum, colnum, sales_value if sales_value else '', NORM_NUM)
                            year_total += sales_value
                            sub_class_totals[colnum] = (sub_class_totals[colnum] + sales_value) if sub_class_totals and colnum in sub_class_totals else sales_value
                            colnum+=1
                        sheet.write(rownum, colnum, year_total if year_total else '', NORM_NUM)
                        sub_class_totals[colnum] = (sub_class_totals[colnum] + year_total) if sub_class_totals and colnum in sub_class_totals else year_total
                        brand_total += year_total
                        colnum += 1
                    sheet.write(rownum, colnum, brand_total if brand_total else '', NORM_NUM)
                    sub_class_totals[colnum] = (sub_class_totals[colnum] + brand_total) if sub_class_totals and colnum in sub_class_totals else brand_total
                    line_total += brand_total
                    colnum += 1
                sheet.write(rownum, colnum, line_total if line_total else '', NORM_NUM)
                sub_class_totals[colnum] = (sub_class_totals[colnum] + line_total) if sub_class_totals and colnum in sub_class_totals else line_total
                rownum += 1
            sheet.write(rownum, 0, str(sub_class) + ' Totals', BLU4_LFT)
            sheet.write(rownum, 1, '', BLU4_LFT)
            for col in range(colnum - 1):
                sheet.write(rownum, col + 2, sub_class_totals.get(col + 2) if sub_class_totals.get(col + 2) else '', BLU4_NUM)
                overall_total[col + 2] = (overall_total[col + 2] + sub_class_totals.get(col + 2)) if overall_total and (col + 2) in overall_total else sub_class_totals.get(col + 2)
            rownum += 1
        sheet.write(rownum, 0, 'Grand Totals', BLU3_LFT)
        sheet.write(rownum, 1, '', BLU3_LFT)
        for col in range(colnum - 1):
            sheet.write(rownum, col + 2, overall_total.get(col + 2) if overall_total.get(col + 2) else '', BLU3_NUM)


        #####TOTAL
        #Header part
        rownum += 3
        sheet.merge_range(rownum, 0, rownum + 1, 0, 'Sub Classification', BLU1_CNT)
        sheet.merge_range(rownum, 1, rownum + 1, 1, 'Salesman', BLU1_CNT)
        colnum = 2
        for year in years:
            year_period = sorted(set([period for period in periods if datetime.strptime(period, '%Y-%m').strftime('%Y') == year])) #Variable created to check the number of months on same year
            year_mon = [datetime.strptime(period, '%Y-%m').strftime('%b') for period in periods if datetime.strptime(period, '%Y-%m').strftime('%Y') == year]
            yr_end_col = colnum - 1 + len(year_period)
            sheet.set_column(colnum, yr_end_col, 15)
            sheet.write(rownum, colnum, year, BLU1_CNT) if colnum == yr_end_col else sheet.merge_range(rownum, colnum, rownum, yr_end_col, year, BLU1_CNT)
            for mon in year_mon:
                sheet.write(rownum + 1, colnum, mon, BLU1_CNT)
                colnum += 1
            sheet.set_column(colnum, colnum, 15)
            sheet.merge_range(rownum, colnum, rownum +1, colnum, str(year) + ' Total', BLU1_CNT)
            colnum += 1
        # sheet.set_column(colnum, colnum, 15)
        sheet.merge_range(rownum ,colnum, rownum +1,colnum, 'Grand Total', BLU1_CNT)

        #DETAIL PART
        rownum += 2
        overall_total = {}
        sub_classes = sorted(set([data['customer_sub_classification'] for data in rawdata if data['customer_sub_classification'] and data['account_manager'] == 'Tom']))
        for sub_class in sub_classes:
            salesmen = sorted(set([data['van_salesman'] for data in rawdata if data['van_salesman'] and data['customer_sub_classification'] == sub_class]))
            sub_class_totals = {}
            for salesman in salesmen:
                grand_total = 0
                sheet.write(rownum, 0, sub_class, NORM_LFT)
                sheet.write(rownum, 1, salesman, NORM_LFT)
                colnum = 2
                for year in years:
                    year_total = 0
                    month_nos = [datetime.strptime(period, '%Y-%m').strftime('%m') for period in periods if period.startswith(year)]
                    for month_no in month_nos:
                        sales_value = sum([data['sales_value'] for data in rawdata
                                           if data['customer_sub_classification'] == sub_class
                                           and data['van_salesman'] == salesman
                                           and data['date'].strftime('%Y') == year
                                           and data['date'].strftime('%m') == month_no])
                        sheet.write(rownum, colnum, sales_value if sales_value else '', NORM_NUM)
                        sub_class_totals[colnum] = (sub_class_totals[colnum] + sales_value) if sub_class_totals and colnum in sub_class_totals else sales_value
                        year_total += sales_value
                        colnum += 1
                    #Year Totals
                    sheet.write(rownum, colnum, year_total if year_total else '', NORM_NUM)
                    sub_class_totals[colnum] = (sub_class_totals[colnum] + year_total) if sub_class_totals and colnum in sub_class_totals else year_total
                    grand_total += year_total
                    colnum += 1
                #Line Totals
                sheet.write(rownum, colnum, grand_total if grand_total else '', NORM_NUM)
                sub_class_totals[colnum] = (sub_class_totals[colnum] + grand_total) if sub_class_totals and colnum in sub_class_totals else grand_total
                rownum += 1
            # Sub Class Totals
            sheet.write(rownum, 0, str(sub_class) + ' Totals', BLU4_LFT)
            sheet.write(rownum, 1, '', BLU4_LFT)
            for col in range(colnum - 1):
                sheet.write(rownum, col + 2, sub_class_totals.get(col + 2) if sub_class_totals.get(col + 2) else '', BLU4_NUM)
            rownum += 1
        end_time = time.time()
        duration_detail = {'description' : 'Van Salesman BW Sales Sheet',
                           'time_taken' : end_time - start_time}
        return duration_detail

    def _create_kam_brand_sku_sheet(self, workbook, rawdata):
        start_time = time.time()
        sheet = workbook.add_worksheet('KAM-Brand-SKU')
        BLU1_CNT = workbook.add_format({'bg_color': '#4D93D9', 'align': 'center', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1})
        BLU2_LFT = workbook.add_format({'bg_color': '#78ADE2', 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue'})
        BLU2_NUM = workbook.add_format({'bg_color': '#78ADE2', 'align': 'right', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue', 'num_format': '#,##0.00'})
        BLU3_NUM = workbook.add_format({'bg_color': '#B3D1EF', 'align': 'right', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue', 'num_format': '#,##0.00'})
        BLU3_LFT = workbook.add_format({'bg_color': '#B3D1EF', 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue'})
        BLU4_NUM = workbook.add_format({'bg_color': '#DAE9F8', 'align': 'right', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue', 'num_format': '#,##0.00'})
        BLU4_LFT = workbook.add_format({'bg_color': '#DAE9F8', 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue'})

        NORM_LFT = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'border': 1, 'border_color':'blue'})
        NORM_NUM = workbook.add_format({'align': 'right', 'valign': 'vcenter', 'border': 1, 'num_format': '#,##0.00', 'border_color':'blue'})

        sheet.merge_range(0, 0, 2, 0, 'Account Manager', BLU1_CNT)
        sheet.set_column(0, 0, 15)
        sheet.merge_range(0, 1, 2, 1, 'Master Parent', BLU1_CNT)
        sheet.set_column(1, 1, 20)
        sheet.merge_range(0, 2, 2, 2, 'Brand Name', BLU1_CNT)
        sheet.set_column(2, 2, 15)
        sheet.merge_range(0, 3, 2, 3, 'Product Category', BLU1_CNT)
        sheet.set_column(3, 3, 15)
        sheet.merge_range(0, 4, 2, 4, 'Item Description', BLU1_CNT)
        sheet.set_column(4, 4, 30)

        periods = sorted(set([data['date'].strftime('%Y-%m') for data in rawdata]))
        years = sorted(set([data['date'].strftime('%Y') for data in rawdata]))

        #HEADER PART
        colnum = 5
        for year in years:
            year_period = sorted(set([period for period in periods if datetime.strptime(period, '%Y-%m').strftime('%Y') == year])) #Variable created to check the number of months on same year
            year_mon = [datetime.strptime(period, '%Y-%m').strftime('%b') for period in periods if datetime.strptime(period, '%Y-%m').strftime('%Y') == year]
            yr_end_col = colnum - 1 + (len(year_period) * 2)
            sheet.set_column(colnum, yr_end_col, 15)
            sheet.write(0, colnum, year, BLU1_CNT) if colnum == yr_end_col else sheet.merge_range(0, colnum, 0, yr_end_col, year, BLU1_CNT)
            for mon in year_mon:
                sheet.merge_range(1, colnum, 1, colnum + 1, mon, BLU1_CNT)
                sheet.write(2, colnum, 'Qty in CTN', BLU1_CNT)
                sheet.write(2, colnum + 1, 'Sales', BLU1_CNT)
                colnum += 2
            sheet.set_column(colnum, colnum + 1, 15)
            sheet.merge_range(0, colnum, 2, colnum, str(year) + ' Total QTY in CTN', BLU1_CNT)
            sheet.merge_range(0, colnum + 1 , 2, colnum +1 , str(year) + ' Total Sales', BLU1_CNT)
            colnum += 2
        sheet.set_column(colnum, colnum + 1, 20)
        sheet.merge_range(0 ,colnum, 2, colnum, 'Grand Total Qty in CTN', BLU1_CNT)
        sheet.merge_range(0 ,colnum + 1, 2, colnum + 1, 'Grand Total Sales', BLU1_CNT)

        #DETAIL PART
        rownum = 3
        overall_total = {}
        managers = sorted(set([data['account_manager'] for data in rawdata if data['account_manager']]))
        for manager in managers:
            masters = sorted(set([data['master_parent'] for data in rawdata if data['master_parent'] and data['account_manager'] == manager]))
            manager_totals = {}
            for master in masters:
                brands = sorted(set([data['brand'] for data in rawdata if data['brand'] and data['account_manager'] == manager and data['master_parent'] == master]))
                master_totals = {}
                for brand in brands:
                    categories = sorted(set([data['product_category'] for data in rawdata if data['product_category'] and data['brand'] == brand and data['master_parent'] == master and data['account_manager'] == manager]))
                    brand_totals = {}
                    for category in categories:
                        products = sorted(set([data['product'] for data in rawdata if data['product'] and data['product_category'] == category and data['brand'] == brand and data['master_parent'] == master and data['account_manager'] == manager]))
                        category_totals = {}
                        for product in products:
                            sheet.set_column(colnum, colnum, 15)
                            grand_total_sales = 0
                            grand_total_qty = 0
                            sheet.write(rownum, 0, manager, NORM_LFT)
                            sheet.write(rownum, 1, master, NORM_LFT)
                            sheet.write(rownum, 2, brand, NORM_LFT)
                            sheet.write(rownum, 3, category, NORM_LFT)
                            sheet.write(rownum, 4, product, NORM_LFT)
                            colnum = 5
                            for year in years:
                                year_total_sales = 0
                                year_total_qty = 0
                                month_nos = [datetime.strptime(period, '%Y-%m').strftime('%m') for period in periods if period.startswith(year)]
                                for month_no in month_nos:
                                    ctn_qty = sum([data['quantity_ctn'] for data in rawdata
                                                       if data['quantity_ctn']
                                                       and data['account_manager'] == manager
                                                       and data['master_parent'] == master
                                                       and data['brand'] == brand
                                                       and data['product_category'] == category
                                                       and data['product'] == product
                                                       and data['date'].strftime('%Y') == year
                                                       and data['date'].strftime('%m') == month_no])
                                    sheet.write(rownum, colnum, ctn_qty if ctn_qty else '', NORM_NUM)
                                    category_totals[colnum] = (category_totals[colnum] + ctn_qty) if category_totals and colnum in category_totals else ctn_qty
                                    brand_totals[colnum] = (brand_totals[colnum] + ctn_qty) if brand_totals and colnum in brand_totals else ctn_qty
                                    master_totals[colnum] = (master_totals[colnum] + ctn_qty) if master_totals and colnum in master_totals else ctn_qty
                                    manager_totals[colnum] = (manager_totals[colnum] + ctn_qty) if manager_totals and colnum in manager_totals else ctn_qty
                                    colnum += 1
                                    year_total_qty += ctn_qty
                                    sales_value = sum([data['sales_value'] for data in rawdata
                                                       if data['account_manager'] == manager
                                                       and data['master_parent'] == master
                                                       and data['brand'] == brand
                                                       and data['product_category'] == category
                                                       and data['product'] == product
                                                       and data['date'].strftime('%Y') == year
                                                       and data['date'].strftime('%m') == month_no])
                                    sheet.write(rownum, colnum, sales_value if sales_value else '', NORM_NUM)
                                    category_totals[colnum] = (category_totals[colnum] + sales_value) if category_totals and colnum in category_totals else sales_value
                                    brand_totals[colnum] = (brand_totals[colnum] + sales_value) if brand_totals and colnum in brand_totals else sales_value
                                    master_totals[colnum] = (master_totals[colnum] + sales_value) if master_totals and colnum in master_totals else sales_value
                                    manager_totals[colnum] = (manager_totals[colnum] + sales_value) if manager_totals and colnum in manager_totals else sales_value
                                    colnum += 1
                                    year_total_sales += sales_value
                                # Year Totals
                                sheet.write(rownum, colnum, year_total_qty if year_total_qty else '', NORM_NUM)
                                category_totals[colnum] = (category_totals[colnum] + year_total_qty) if category_totals and colnum in category_totals else year_total_qty
                                brand_totals[colnum] = (brand_totals[colnum] + year_total_qty) if brand_totals and colnum in brand_totals else year_total_qty
                                master_totals[colnum] = (master_totals[colnum] + year_total_qty) if master_totals and colnum in master_totals else year_total_qty
                                manager_totals[colnum] = (manager_totals[colnum] + year_total_qty) if manager_totals and colnum in manager_totals else year_total_qty
                                overall_total[colnum] = (overall_total[colnum] + year_total_qty) if overall_total and colnum in overall_total else year_total_qty
                                grand_total_qty += year_total_qty
                                colnum += 1
                                sheet.write(rownum, colnum, year_total_sales if year_total_sales else '', NORM_NUM)
                                category_totals[colnum] = (category_totals[colnum] + year_total_sales) if category_totals and colnum in category_totals else year_total_sales
                                brand_totals[colnum] = (brand_totals[colnum] + year_total_sales) if brand_totals and colnum in brand_totals else year_total_sales
                                master_totals[colnum] = (master_totals[colnum] + year_total_sales) if master_totals and colnum in master_totals else year_total_sales
                                manager_totals[colnum] = (manager_totals[colnum] + year_total_sales) if manager_totals and colnum in manager_totals else year_total_sales
                                overall_total[colnum] = (overall_total[colnum] + year_total_sales) if overall_total and colnum in overall_total else year_total_sales
                                grand_total_sales += year_total_sales
                                colnum += 1
                            # Line Totals
                            sheet.write(rownum, colnum, grand_total_qty if grand_total_qty else '', NORM_NUM)
                            category_totals[colnum] = (category_totals[colnum] + grand_total_qty) if category_totals and colnum in category_totals else grand_total_qty
                            brand_totals[colnum] = (brand_totals[colnum] + grand_total_qty) if brand_totals and colnum in brand_totals else grand_total_qty
                            master_totals[colnum] = (master_totals[colnum] + grand_total_qty) if master_totals and colnum in master_totals else grand_total_qty
                            manager_totals[colnum] = (manager_totals[colnum] + grand_total_qty) if manager_totals and colnum in manager_totals else grand_total_qty
                            overall_total[colnum] = (overall_total[colnum] + grand_total_qty) if overall_total and colnum in overall_total else grand_total_qty
                            colnum += 1
                            sheet.write(rownum, colnum, grand_total_sales if grand_total_sales else '', NORM_NUM)
                            category_totals[colnum] = (category_totals[colnum] + grand_total_sales) if category_totals and colnum in category_totals else grand_total_sales
                            brand_totals[colnum] = (brand_totals[colnum] + grand_total_sales) if brand_totals and colnum in brand_totals else grand_total_sales
                            master_totals[colnum] = (master_totals[colnum] + grand_total_sales) if master_totals and colnum in master_totals else grand_total_sales
                            manager_totals[colnum] = (manager_totals[colnum] + grand_total_sales) if manager_totals and colnum in manager_totals else grand_total_sales
                            overall_total[colnum] = (overall_total[colnum] + grand_total_sales) if overall_total and colnum in overall_total else grand_total_sales
                            rownum += 1
                        # Category Totals
                        sheet.write(rownum, 0, manager, BLU4_LFT)
                        sheet.write(rownum, 1, master, BLU4_LFT)
                        sheet.write(rownum, 2, brand, BLU4_LFT)
                        sheet.write(rownum, 3, str(category) + ' Totals', BLU4_LFT)
                        for col in range(4, colnum + 1):
                            sheet.write(rownum, col, category_totals.get(col) if category_totals.get(col) else '', BLU4_NUM)
                        rownum += 1
                    # Brand Totals
                    sheet.write(rownum, 0, manager, BLU3_LFT)
                    sheet.write(rownum, 1, master, BLU3_LFT)
                    sheet.write(rownum, 2, str(brand) + ' Totals', BLU3_LFT)
                    sheet.write(rownum, 3, '', BLU3_LFT)
                    for col in range(4, colnum + 1):
                        sheet.write(rownum, col, brand_totals.get(col) if brand_totals.get(col) else '',BLU3_NUM)
                    rownum += 1
                # Master Totals
                sheet.write(rownum, 0, manager, BLU2_LFT)
                sheet.write(rownum, 1, str(master) + ' Totals', BLU2_LFT)
                sheet.write(rownum, 2, '', BLU2_LFT)
                sheet.write(rownum, 3, '', BLU2_LFT)
                for col in range(4, colnum + 1):
                    sheet.write(rownum, col, master_totals.get(col) if master_totals.get(col) else '',BLU2_NUM)
                rownum += 1
            # Manager Totals
            sheet.write(rownum, 0, str(manager) + ' Totals', BLU1_CNT)
            sheet.write(rownum, 1, '', BLU1_CNT)
            sheet.write(rownum, 2, '', BLU1_CNT)
            sheet.write(rownum, 3, '', BLU1_CNT)
            for col in range(4, colnum + 1):
                sheet.write(rownum, col, manager_totals.get(col) if manager_totals.get(col) else '',BLU1_CNT)
            rownum += 1
        #Overall Totals
        sheet.write(rownum, 0, 'Grand Total', BLU1_CNT)
        sheet.write(rownum, 1, '', BLU1_CNT)
        sheet.write(rownum, 2, '', BLU1_CNT)
        sheet.write(rownum, 3, '', BLU1_CNT)
        for col in range(4, colnum + 1):
            sheet.write(rownum, col, overall_total.get(col) if overall_total.get(col) else '', BLU1_CNT)
        rownum += 1
        end_time = time.time()
        duration_detail = {'description' : 'KAM Brand SKU',
                           'time_taken' : end_time - start_time}
        return duration_detail

    def _create_daily_sales_value_sheet(self, workbook, rawdata):
        start_time = time.time()
        sheet = workbook.add_worksheet('Daily Sales Value')
        BLU1_CNT = workbook.add_format({'bg_color': '#4D93D9', 'align': 'center', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri','border': 1})
        NORM_LFT = workbook.add_format({'align': 'left', 'valign': 'vcenter','border': 1, 'border_color':'blue'})
        NORM_NUM = workbook.add_format({'align': 'right', 'valign': 'vcenter','border': 1,'num_format': '#,##0.00', 'border_color':'blue'})
        LBLUE_NUM = workbook.add_format({'bg_color': '#DDEBF7', 'align': 'right', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1,'num_format': '#,##0.00'})
        LBLUE_TXT = workbook.add_format({'bg_color': '#DDEBF7', 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1})
        MBLUE_TXT = workbook.add_format({'bg_color': '#BDD7EE', 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1})
        MBLUE_NUM = workbook.add_format({'bg_color': '#BDD7EE', 'align': 'right', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1,'num_format': '#,##0.00'})

        sheet.merge_range(0, 0, 1, 0, 'Day', BLU1_CNT)
        sheet.set_column(0, 0, 15)
        sheet.merge_range(0, 1, 1, 1, 'Trade Channel', BLU1_CNT)
        sheet.set_column(1, 1, 20)
        sheet.merge_range(0, 2, 1, 2, 'Customer Classification', BLU1_CNT)
        sheet.set_column(2, 2, 40)

        periods = sorted(set([data['date'].strftime('%Y-%m') for data in rawdata]))
        years = sorted(set([data['date'].strftime('%Y') for data in rawdata]))

        #HEADER PART
        colnum = 3
        for year in years:
            year_period = sorted(set([period for period in periods if datetime.strptime(period, '%Y-%m').strftime('%Y') == year])) #Variable created to check the number of months on same year
            year_mon = [datetime.strptime(period, '%Y-%m').strftime('%b') for period in periods if datetime.strptime(period, '%Y-%m').strftime('%Y') == year]
            yr_end_col = colnum - 1 + len(year_period)
            sheet.set_column(colnum, yr_end_col, 15)
            sheet.write(0, colnum, year, BLU1_CNT) if colnum == yr_end_col else sheet.merge_range(0, colnum, 0, yr_end_col, year, BLU1_CNT)
            for mon in year_mon:
                sheet.write(1, colnum, mon, BLU1_CNT)
                colnum += 1
            sheet.set_column(colnum, colnum, 15)
            sheet.merge_range(0, colnum, 1, colnum, str(year) + ' Total', BLU1_CNT)
            colnum += 1
        sheet.set_column(colnum, colnum, 15)
        sheet.merge_range(0 ,colnum, 1,colnum, 'Grand Total', BLU1_CNT)

        #DETAIL PART
        rownum = 2
        overall_total = {}
        for day in range(1, 32):
            channels = sorted(set([data['trade_channel'] for data in rawdata if data['trade_channel']]))
            day_totals = {}
            for channel in channels:
                loop_classes = sorted(set([data['customer_classification'] for data in rawdata if data['customer_classification']
                                           and data['trade_channel'] == channel and data['customer_classification'] not in ('INTERCOMPANY')]))
                for cls in loop_classes:
                    line_total = 0
                    sheet.write(rownum, 0, day, NORM_LFT)
                    sheet.write(rownum, 1, channel, NORM_LFT)
                    sheet.write(rownum, 2, cls, NORM_LFT)
                    colnum = 3
                    for year in years:
                        year_total = 0
                        month_nos = [datetime.strptime(period, '%Y-%m').strftime('%m') for period in periods if period.startswith(year)]
                        for month_no in month_nos:
                            sales_value = sum([data['sales_value'] for data in rawdata
                                               if data['trade_channel'] == channel
                                               and data['customer_classification'] == cls
                                               and data['date'].strftime('%Y') == year
                                               and data['date'].strftime('%m') == month_no
                                               and data['date'].strftime('%d') == str(day).zfill(2)
                                               and data['move_type'] == 'out_invoice'])
                            year_total += sales_value
                            sheet.write(rownum, colnum, sales_value if sales_value else '', NORM_NUM)
                            day_totals[colnum] = (day_totals[colnum] + sales_value) if day_totals and colnum in day_totals else sales_value
                            overall_total[colnum] = (overall_total[colnum] + sales_value) if overall_total and colnum in overall_total else sales_value
                            colnum += 1
                        sheet.write(rownum, colnum, year_total if year_total else '', NORM_NUM)
                        day_totals[colnum] = (day_totals[colnum] + year_total) if day_totals and colnum in day_totals else year_total
                        overall_total[colnum] = (overall_total[colnum] + year_total) if overall_total and colnum in overall_total else year_total
                        line_total += year_total
                        colnum += 1
                    sheet.write(rownum, colnum, line_total, NORM_NUM)
                    day_totals[colnum] = (day_totals[colnum] + line_total) if day_totals and colnum in day_totals else line_total
                    overall_total[colnum] = (overall_total[colnum] + line_total) if overall_total and colnum in overall_total else line_total
                    rownum += 1
            sheet.write(rownum, 0, str(day) + ' Total', LBLUE_TXT)
            sheet.write(rownum, 1, '', LBLUE_TXT)
            for col in range(colnum - 1):
                sheet.write(rownum, col + 2, day_totals.get(col + 2) if day_totals.get(col + 2) else '', LBLUE_NUM)
            rownum += 1
        sheet.write(rownum, 0, 'Grand Totals', MBLUE_TXT)
        sheet.write(rownum, 1, '', MBLUE_TXT)
        for col in range(colnum - 1):
            sheet.write(rownum, col + 2, overall_total.get(col + 2) if overall_total.get(col + 2) else '', MBLUE_NUM)
        rownum += 1
        end_time = time.time()
        duration_detail = {'description' : 'Daily Sales Value Sheet',
                           'time_taken' : end_time - start_time}
        return duration_detail

    def _create_brand_skuwise_sheet(self, workbook, rawdata):
        start_time = time.time()
        sheet = workbook.add_worksheet('Brand-SKU Wise')
        BLU1_CNT = workbook.add_format({'bg_color': '#4D93D9', 'align': 'center', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1})
        BLU2_LFT = workbook.add_format({'bg_color': '#78ADE2', 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue'})
        BLU2_NUM = workbook.add_format({'bg_color': '#78ADE2', 'align': 'right', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue', 'num_format': '#,##0.00'})
        BLU3_NUM = workbook.add_format({'bg_color': '#B3D1EF', 'align': 'right', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue', 'num_format': '#,##0.00'})
        BLU3_LFT = workbook.add_format({'bg_color': '#B3D1EF', 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue'})
        BLU4_NUM = workbook.add_format({'bg_color': '#DAE9F8', 'align': 'right', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue', 'num_format': '#,##0.00'})
        BLU4_LFT = workbook.add_format({'bg_color': '#DAE9F8', 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue'})

        NORM_LFT = workbook.add_format({'align': 'left', 'valign': 'vcenter','border': 1, 'border_color':'blue'})
        NORM_NUM = workbook.add_format({'align': 'right', 'valign': 'vcenter','border': 1,'num_format': '#,##0.00', 'border_color':'blue'})

        sheet.merge_range(0, 0, 2, 0, 'Brand Name', BLU1_CNT)
        sheet.set_column(0, 0, 15)
        sheet.merge_range(0, 1, 2, 1, 'Product Category', BLU1_CNT)
        sheet.set_column(1, 1, 20)
        sheet.merge_range(0, 2, 2, 2, 'Item Description', BLU1_CNT)
        sheet.set_column(2, 2, 40)

        periods = sorted(set([data['date'].strftime('%Y-%m') for data in rawdata]))
        years = sorted(set([data['date'].strftime('%Y') for data in rawdata]))

        #HEADER PART
        colnum = 3
        for year in years:
            year_period = sorted(set([period for period in periods if datetime.strptime(period, '%Y-%m').strftime('%Y') == year])) #Variable created to check the number of months on same year
            year_mon = [datetime.strptime(period, '%Y-%m').strftime('%b') for period in periods if datetime.strptime(period, '%Y-%m').strftime('%Y') == year]
            yr_end_col = colnum - 1 + (len(year_period) * 2)
            sheet.set_column(colnum, yr_end_col, 15)
            sheet.write(0, colnum, year, BLU1_CNT) if colnum == yr_end_col else sheet.merge_range(0, colnum, 0, yr_end_col, year, BLU1_CNT)
            for mon in year_mon:
                sheet.merge_range(1, colnum, 1, colnum + 1, mon, BLU1_CNT)
                sheet.write(2, colnum, 'Qty in CTN', BLU1_CNT)
                sheet.write(2, colnum + 1, 'Sales', BLU1_CNT)
                colnum += 2
            sheet.set_column(colnum, colnum + 1, 15)
            sheet.merge_range(0, colnum, 2, colnum, str(year) + ' Total QTY in CTN', BLU1_CNT)
            sheet.merge_range(0, colnum + 1 , 2, colnum +1 , str(year) + ' Total Sales', BLU1_CNT)
            colnum += 2
        sheet.set_column(colnum, colnum + 1, 20)
        sheet.merge_range(0 ,colnum, 2, colnum, 'Grand Total Qty in CTN', BLU1_CNT)
        sheet.merge_range(0 ,colnum + 1, 2, colnum + 1, 'Grand Total Sales', BLU1_CNT)

        #DETAIL PART
        rownum = 3
        overall_total = {}
        brands = sorted(set([data['brand'] for data in rawdata if data['brand']]))
        for brand in brands:
            categories = sorted(set([data['product_category'] for data in rawdata if data['product_category'] and data['brand'] == brand]))
            brand_totals = {}
            for category in categories:
                products = sorted(set([data['product'] for data in rawdata if data['product'] and data['product_category'] == category and data['brand'] == brand]))
                category_total = {}
                for product in products:
                    sheet.set_column(colnum, colnum, 15)
                    grand_total_sales = 0
                    grand_total_qty = 0
                    sheet.write(rownum, 0, brand, NORM_LFT)
                    sheet.write(rownum, 1, category, NORM_LFT)
                    sheet.write(rownum, 2, product, NORM_LFT)
                    colnum = 3
                    for year in years:
                        year_total_sales = 0
                        year_total_qty = 0
                        month_nos = [datetime.strptime(period, '%Y-%m').strftime('%m') for period in periods if period.startswith(year)]
                        for month_no in month_nos:
                            sales_value = sum([data['sales_value'] for data in rawdata
                                               if data['brand'] == brand
                                               and data['product_category'] == category
                                               and data['product'] == product
                                               and data['date'].strftime('%Y') == year
                                               and data['date'].strftime('%m') == month_no])
                            sheet.write(rownum, colnum, sales_value if sales_value else '', NORM_NUM)
                            category_total[colnum] = (category_total[colnum] + sales_value) if category_total and colnum in category_total else sales_value
                            brand_totals[colnum] = (brand_totals[colnum] + sales_value) if brand_totals and colnum in brand_totals else sales_value
                            overall_total[colnum] = (overall_total[colnum] + sales_value) if overall_total and colnum in overall_total else sales_value
                            colnum += 1
                            year_total_sales += sales_value
                            ctn_qty = sum([data['quantity_ctn'] for data in rawdata
                                               if data['quantity_ctn']
                                               and data['brand'] == brand
                                               and data['product_category'] == category
                                               and data['product'] == product
                                               and data['date'].strftime('%Y') == year
                                               and data['date'].strftime('%m') == month_no])
                            sheet.write(rownum, colnum, ctn_qty if ctn_qty else '', NORM_NUM)
                            category_total[colnum] = (category_total[colnum] + ctn_qty) if category_total and colnum in category_total else ctn_qty
                            brand_totals[colnum] = (brand_totals[colnum] + ctn_qty) if brand_totals and colnum in brand_totals else ctn_qty
                            overall_total[colnum] = (overall_total[colnum] + ctn_qty) if overall_total and colnum in overall_total else ctn_qty
                            colnum += 1
                            year_total_qty += ctn_qty
                        # Year Totals
                        sheet.write(rownum, colnum, year_total_sales if year_total_sales else '', NORM_NUM)
                        category_total[colnum] = (category_total[colnum] + year_total_sales) if category_total and colnum in category_total else year_total_sales
                        brand_totals[colnum] = (brand_totals[colnum] + year_total_sales) if brand_totals and colnum in brand_totals else year_total_sales
                        overall_total[colnum] = (overall_total[colnum] + year_total_sales) if overall_total and colnum in overall_total else year_total_sales
                        grand_total_sales += year_total_sales
                        colnum += 1
                        sheet.write(rownum, colnum, year_total_qty if year_total_qty else '', NORM_NUM)
                        category_total[colnum] = (category_total[colnum] + year_total_qty) if category_total and colnum in category_total else year_total_qty
                        brand_totals[colnum] = (brand_totals[colnum] + year_total_qty) if brand_totals and colnum in brand_totals else year_total_qty
                        overall_total[colnum] = (overall_total[colnum] + year_total_qty) if overall_total and colnum in overall_total else year_total_qty
                        grand_total_qty += year_total_qty
                        colnum += 1
                    # Line Totals
                    sheet.write(rownum, colnum, grand_total_sales if grand_total_sales else '', NORM_NUM)
                    category_total[colnum] = (category_total[colnum] + grand_total_sales) if category_total and colnum in category_total else grand_total_sales
                    brand_totals[colnum] = (brand_totals[colnum] + grand_total_sales) if brand_totals and colnum in brand_totals else grand_total_sales
                    overall_total[colnum] = (overall_total[colnum] + grand_total_sales) if overall_total and colnum in overall_total else grand_total_sales
                    colnum += 1
                    sheet.write(rownum, colnum, grand_total_sales if grand_total_qty else '', NORM_NUM)
                    category_total[colnum] = (category_total[colnum] + grand_total_qty) if category_total and colnum in category_total else grand_total_qty
                    brand_totals[colnum] = (brand_totals[colnum] + grand_total_qty) if brand_totals and colnum in brand_totals else grand_total_qty
                    overall_total[colnum] = (overall_total[colnum] + grand_total_qty) if overall_total and colnum in overall_total else grand_total_qty
                    rownum += 1
                #Category Totals
                sheet.write(rownum, 0, brand, BLU4_LFT)
                sheet.write(rownum, 1, str(category) + ' Totals', BLU4_LFT)
                for col in range(colnum - 1):
                    sheet.write(rownum, col + 2, category_total.get(col + 2) if category_total.get(col + 2) else '', BLU4_NUM)
                rownum += 1
            #Brand Totals
            sheet.write(rownum, 0, str(brand) + ' Totals', BLU3_LFT)
            sheet.write(rownum, 1, '', BLU3_LFT)
            for col in range(colnum - 1):
                sheet.write(rownum, col + 2, brand_totals.get(col + 2) if brand_totals.get(col + 2) else '', BLU3_NUM)
            rownum += 1
        #Overall Totals
        sheet.write(rownum, 0, 'Grand Total', BLU2_LFT)
        sheet.write(rownum, 1, '', BLU2_LFT)
        for col in range(colnum - 1):
            sheet.write(rownum, col + 2, overall_total.get(col + 2) if overall_total.get(col + 2) else '', BLU2_NUM)
        rownum += 1
        end_time = time.time()
        duration_detail = {'description' : 'Creating Brand SKU Wise Sheet',
                           'time_taken' : end_time - start_time}
        return duration_detail

    def _create_brand_customergroup_sheet(self, workbook, rawdata):
        start_time = time.time()
        sheet = workbook.add_worksheet('Brand-Customer Group')
        years = sorted(set([data['date'].strftime('%Y') for data in rawdata]))
        periods = sorted(set([data['date'].strftime('%Y-%m') for data in rawdata]))

        BLU1_CNT = workbook.add_format({'bg_color': '#4D93D9', 'align': 'center', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1})
        BLU2_LFT = workbook.add_format({'bg_color': '#78ADE2', 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue'})
        BLU2_NUM = workbook.add_format({'bg_color': '#78ADE2', 'align': 'right', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue', 'num_format': '#,##0.00'})
        BLU3_LFT = workbook.add_format({'bg_color': '#B3D1EF', 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue'})
        BLU3_NUM = workbook.add_format({'bg_color': '#B3D1EF', 'align': 'right', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue', 'num_format': '#,##0.00'})
        BLU4_LFT = workbook.add_format({'bg_color': '#DAE9F8', 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue'})
        BLU4_NUM = workbook.add_format({'bg_color': '#DAE9F8', 'align': 'right', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue', 'num_format': '#,##0.00'})
        NORM_LFT = workbook.add_format({'align': 'left', 'valign': 'vcenter','border': 1, 'border_color':'blue'})
        NORM_NUM = workbook.add_format({'align': 'right', 'valign': 'vcenter','border': 1,'num_format': '#,##0.00', 'border_color':'blue'})


        sheet.merge_range(0, 0, 1, 0, 'Brand Name', BLU1_CNT)
        sheet.set_column(0, 0, 15)
        sheet.merge_range(0, 1, 1, 1, 'Product Category', BLU1_CNT)
        sheet.set_column(1, 1, 20)
        sheet.merge_range(0, 2, 1, 2, 'Master Parent', BLU1_CNT)
        sheet.set_column(2, 2, 30)

        #HEADER PART
        colnum = 3
        for year in years:
            year_period = sorted(set([period for period in periods if datetime.strptime(period, '%Y-%m').strftime('%Y') == year])) #Variable created to check the number of months on same year
            year_mon = [datetime.strptime(period, '%Y-%m').strftime('%b') for period in periods if datetime.strptime(period, '%Y-%m').strftime('%Y') == year]
            yr_end_col = colnum - 1 + len(year_period)
            sheet.set_column(colnum, yr_end_col, 15)
            sheet.write(0, colnum, year, BLU1_CNT) if colnum == yr_end_col else sheet.merge_range(0, colnum, 0, yr_end_col, year, BLU1_CNT)
            for mon in year_mon:
                sheet.write(1, colnum, mon, BLU1_CNT)
                colnum += 1
            sheet.set_column(colnum, colnum, 15)
            sheet.merge_range(0, colnum, 1, colnum, str(year) + ' Total', BLU1_CNT)
            colnum += 1
        sheet.set_column(colnum, colnum, 15)
        sheet.merge_range(0 ,colnum, 1,colnum, 'Grand Total', BLU1_CNT)

        #DETAIL PART
        rownum = 2
        overall_total = {}
        brands = sorted(set([data['brand'] for data in rawdata if data['brand']]))
        for brand in brands:
            categories = sorted(set([data['product_category'] for data in rawdata if data['product_category'] and data['brand'] == brand]))
            brand_totals = {}
            for category in categories:
                masters = sorted(set([data['master_parent'] for data in rawdata if data['master_parent'] and data['product_category'] == category and data['brand'] == brand]))
                category_total = {}
                for master in masters:
                    sheet.set_column(colnum, colnum, 15)
                    grand_total = 0
                    sheet.write(rownum, 0, brand, NORM_LFT)
                    sheet.write(rownum, 1, category, NORM_LFT)
                    sheet.write(rownum, 2, master, NORM_LFT)
                    colnum = 3
                    for year in years:
                        year_total = 0
                        month_nos = [datetime.strptime(period, '%Y-%m').strftime('%m') for period in periods if period.startswith(year)]
                        for month_no in month_nos:
                            sales_value = sum([data['sales_value'] for data in rawdata
                                               if data['brand'] == brand
                                               and data['product_category'] == category
                                               and data['master_parent'] == master
                                               and data['date'].strftime('%Y') == year
                                               and data['date'].strftime('%m') == month_no])
                            sheet.write(rownum, colnum, sales_value if sales_value else '', NORM_NUM)
                            category_total[colnum] = (category_total[colnum] + sales_value) if category_total and colnum in category_total else sales_value
                            brand_totals[colnum] = (brand_totals[colnum] + sales_value) if brand_totals and colnum in brand_totals else sales_value
                            overall_total[colnum] = (overall_total[colnum] + sales_value) if overall_total and colnum in overall_total else sales_value
                            year_total += sales_value
                            colnum += 1
                        #Year Totals
                        sheet.write(rownum, colnum, year_total if year_total else '', NORM_NUM)
                        category_total[colnum] = (category_total[colnum] + year_total) if category_total and colnum in category_total else year_total
                        brand_totals[colnum] = (brand_totals[colnum] + year_total) if brand_totals and colnum in brand_totals else year_total
                        grand_total += year_total
                        colnum += 1
                    #Line Totals
                    sheet.write(rownum, colnum, grand_total if grand_total else '', NORM_NUM)
                    category_total[colnum] = (category_total[colnum] + grand_total) if category_total and colnum in category_total else grand_total
                    brand_totals[colnum] = (brand_totals[colnum] + grand_total) if brand_totals and colnum in brand_totals else grand_total
                    rownum += 1
                #Category Totals
                sheet.write(rownum, 0, brand, BLU4_LFT)
                sheet.write(rownum, 1, str(category) + ' Totals', BLU4_LFT)
                for col in range(colnum - 1):
                    sheet.write(rownum, col + 2, category_total.get(col + 2) if category_total.get(col + 2) else '', BLU4_NUM)
                rownum += 1
            #Brand Totals
            sheet.write(rownum, 0, str(brand) + ' Totals', BLU3_LFT)
            sheet.write(rownum, 1, '', BLU3_LFT)
            for col in range(colnum - 1):
                sheet.write(rownum, col + 2, brand_totals.get(col + 2) if brand_totals.get(col + 2) else '', BLU3_NUM)
            rownum += 1
        #Overall Totals
        sheet.write(rownum, 0, 'Grand Total', BLU2_LFT)
        sheet.write(rownum, 1, '', BLU2_LFT)
        for col in range(colnum - 1):
            sheet.write(rownum, col + 2, brand_totals.get(col + 2) if brand_totals.get(col + 2) else '', BLU2_NUM)
        rownum += 1
        end_time = time.time()
        duration_detail = {'description' : 'Creating Brand Customer Group Sheet',
                           'time_taken' : end_time - start_time}
        return duration_detail

    def _create_brand_tradechannel_sheet(self, workbook, rawdata):
        start_time = time.time()
        sheet = workbook.add_worksheet('Brand-Trade Channel')
        years = sorted(set([data['date'].strftime('%Y') for data in rawdata]))
        periods = sorted(set([data['date'].strftime('%Y-%m') for data in rawdata]))
        sub_class = sorted(set([data['customer_classification'] for data in rawdata if data['customer_classification'] and data['customer_classification'] not in ('INTERCOMPANY')]))
        channels = sorted(set([data['trade_channel'] for data in rawdata if data['trade_channel']]))

        #FORMAT DECLARATION
        DBLUE_CNT = workbook.add_format({'bg_color': '#9BC2E6', 'align': 'center', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1})
        MBLUE_NUM = workbook.add_format({'bg_color': '#BDD7EE', 'align': 'right', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1,'num_format': '#,##0.00'})
        MBLUE_TXT = workbook.add_format({'bg_color': '#BDD7EE', 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1})
        LBLUE_NUM = workbook.add_format({'bg_color': '#DDEBF7', 'align': 'right', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1,'num_format': '#,##0.00'})
        LBLUE_TXT = workbook.add_format({'bg_color': '#DDEBF7', 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1})
        NORM_NUM = workbook.add_format({'align': 'right', 'valign': 'vcenter','border': 1,'num_format': '#,##0.00'})

        #HEADER PART
        sheet.merge_range(0, 0, 3, 0, 'Brand Name', DBLUE_CNT)
        sheet.merge_range(0, 1, 3, 1, 'Product Category', DBLUE_CNT)

        #year row formating
        start_col = 2
        for year in years:
            year_period = sorted(set([period for period in periods if datetime.strptime(period, '%Y-%m').strftime('%Y') == year])) #Variable created to check the number of months on same year
            year_mon = [datetime.strptime(period, '%Y-%m').strftime('%B') for period in periods if datetime.strptime(period, '%Y-%m').strftime('%Y') == year] #To get monthname list.
            yr_end_col = start_col + (len(sub_class) * len(year_period)) + len(year_period) - 1
            sheet.merge_range(0, start_col, 0, yr_end_col, year, DBLUE_CNT)
            sheet.merge_range(0, yr_end_col + 1, 3, yr_end_col + 1, str(year) + ' Total', DBLUE_CNT)
            for mon in year_mon:
                mon_end_col = start_col + len(sub_class) - 1
                sheet.merge_range(1, start_col, 1, mon_end_col, mon, DBLUE_CNT)
                for channel in channels:
                    loop_classes = sorted(set([data['customer_classification'] for data in rawdata if data['customer_classification'] and data['trade_channel'] == channel and data['customer_classification'] not in ('INTERCOMPANY')]))
                    for cls in loop_classes:
                        sheet.write(2, start_col, channel, DBLUE_CNT)
                        sheet.write(3, start_col, cls, DBLUE_CNT)
                        start_col += 1
                sheet.merge_range(1, mon_end_col + 1, 3, mon_end_col + 1, str(mon) + ' Total', DBLUE_CNT)
                start_col =  mon_end_col + 2
            start_col = yr_end_col + 2
        sheet.merge_range(0, start_col, 3, start_col, 'Grand Total', DBLUE_CNT)

        #DETAIL PART
        rownum = 4
        overall_total = {}
        brands = sorted(set([data['brand'] for data in rawdata if data['brand']]))
        for brand in brands:
            categories = sorted(set([data['product_category'] for data in rawdata if data['product_category'] and data['brand'] == brand]))
            brand_totals = {}
            for category in categories:
                colnum = 2
                sheet.set_column(colnum, colnum, 15)
                grand_total = 0
                sheet.set_column(0, 0, 22)
                sheet.write(rownum, 0, brand, MBLUE_TXT)
                sheet.set_column(1, 1, 22)
                sheet.write(rownum, 1, category, MBLUE_TXT)
                for year in years:
                    year_total = 0
                    month_nos = [datetime.strptime(period, '%Y-%m').strftime('%m') for period in periods if period.startswith(year)]
                    for month_no in month_nos:
                        month_total = 0
                        for channel in channels:
                            loop_classes = sorted(set([data['customer_classification'] for data in rawdata
                                                       if data['customer_classification'] and data['trade_channel'] == channel and data['customer_classification'] not in ('INTERCOMPANY')]))
                            for cls in loop_classes:
                                sales_value = sum([data['sales_value'] for data in rawdata
                                                   if data['brand'] == brand
                                                   and data['product_category'] == category
                                                   and data['trade_channel'] == channel
                                                   and data['customer_classification'] == cls
                                                   and data['date'].strftime('%Y') == year
                                                   and data['date'].strftime('%m') == month_no])
                                month_total += sales_value
                                sheet.write(rownum, colnum, sales_value, NORM_NUM)
                                brand_totals[colnum] = (brand_totals[colnum] + sales_value) if brand_totals and colnum in brand_totals else sales_value
                                overall_total[colnum] = (overall_total[colnum] + sales_value) if overall_total and colnum in overall_total else sales_value
                                colnum += 1
                                sheet.set_column(colnum, colnum, 15)
                        sheet.write(rownum, colnum, month_total, NORM_NUM)
                        year_total += month_total
                        colnum += 1
                        sheet.set_column(colnum, colnum, 15)
                    sheet.write(rownum, colnum, year_total, NORM_NUM)
                    grand_total += year_total
                    colnum += 1
                    sheet.set_column(colnum, colnum, 15)
                sheet.write(rownum, colnum, grand_total, NORM_NUM)
                rownum += 1
            sheet.write(rownum, 0, str(brand) + ' Totals', LBLUE_TXT)
            sheet.write(rownum, 1, '', LBLUE_TXT)
            for col in range(colnum - 1):
                sheet.write(rownum, col + 2, brand_totals.get(col + 2) if brand_totals.get(col + 2) else '', LBLUE_NUM)
            rownum += 1
        sheet.write(rownum, 0, 'Grand Totals', MBLUE_TXT)
        sheet.write(rownum, 1, '', MBLUE_TXT)
        for col in range(colnum - 1):
            sheet.write(rownum, col + 2, overall_total.get(col + 2) if overall_total.get(col + 2) else '', MBLUE_NUM)
        rownum += 1
        end_time = time.time()
        duration_detail = {'description' : 'Creating Brand Trade Channel Sheet',
                           'time_taken' : end_time - start_time}
        return duration_detail

    def _create_tradechannel_sheet(self, workbook, rawdata):
        if not rawdata:
            return
        start_time = time.time()
        # sheet = workbook.add_worksheet('Trade Channel')
        # BLU1_CNT = workbook.add_format({'bg_color': '#4D93D9', 'align': 'center', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1})
        # BLU4_NUM = workbook.add_format({'bg_color': '#DAE9F8', 'align': 'right', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue', 'num_format': '#,##0.00'})
        # BLU4_LFT = workbook.add_format({'bg_color': '#DAE9F8', 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'border_color':'blue'})
        # NORM_LFT = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'border': 1, 'border_color':'blue'})
        # NORM_NUM = workbook.add_format({'align': 'right', 'valign': 'vcenter','border': 1,'num_format': '#,##0.00', 'border_color':'blue'})
        #
        # periods = sorted(set([data['date'].strftime('%Y-%m') for data in rawdata]))
        # years = sorted(set([data['date'].strftime('%Y') for data in rawdata]))
        #
        # sheet.merge_range(0, 0, 1, 0, 'Trade Channel', BLU1_CNT)
        # sheet.set_column(0, 0, 15)
        # sheet.merge_range(0, 1, 1, 1, 'Customer Classification', BLU1_CNT)
        # sheet.set_column(1, 1, 20)
        #
        # #HEADER PART
        # colnum = 2
        # for year in years:
        #     year_period = sorted(set([period for period in periods if datetime.strptime(period, '%Y-%m').strftime('%Y') == year])) #Variable created to check the number of months on same year
        #     year_mon = [datetime.strptime(period, '%Y-%m').strftime('%b') for period in periods if datetime.strptime(period, '%Y-%m').strftime('%Y') == year]
        #     yr_end_col = colnum - 1 + len(year_period)
        #     sheet.set_column(colnum, yr_end_col, 15)
        #     sheet.write(0, colnum, year, BLU1_CNT) if colnum == yr_end_col else sheet.merge_range(0, colnum, 0, yr_end_col, year, BLU1_CNT)
        #     for mon in year_mon:
        #         sheet.write(1, colnum, mon, BLU1_CNT)
        #         colnum += 1
        #     sheet.set_column(colnum, colnum, 15)
        #     sheet.merge_range(0, colnum, 1, colnum, str(year) + ' Total', BLU1_CNT)
        #     colnum += 1
        # sheet.set_column(colnum, colnum, 15)
        # sheet.merge_range(0, colnum, 1, colnum, 'Grand Total', BLU1_CNT)
        #
        # #Detail Part
        # rownum = 2
        # channels = sorted(set([data['trade_channel'] for data in rawdata if data['trade_channel']]))
        # for channel in channels:
        #     classes = sorted(set([data['customer_classification'] for data in rawdata
        #                                if data['customer_classification'] and data['trade_channel'] == channel
        #                                and data['customer_classification'] not in ('INTERCOMPANY')]))
        #     channel_totals = {}
        #     for cls in classes:
        #         line_total = 0
        #         sheet.write(rownum, 0, channel, NORM_LFT)
        #         sheet.write(rownum, 1, cls, NORM_LFT)
        #         colnum = 3
        #         for year in years:
        #             year_total = 0
        #             month_nos = [datetime.strptime(period, '%Y-%m').strftime('%m') for period in periods if period.startswith(year)]
        #             for month_no in month_nos:
        #                 sales_value = sum([data['sales_value'] for data in rawdata
        #                                    if data['trade_channel'] == channel
        #                                    and data['customer_classification'] == cls
        #                                    and data['date'].strftime('%Y') == year
        #                                    and data['date'].strftime('%m') == month_no])
        #                 sheet.write(rownum, colnum, sales_value if sales_value else '', NORM_NUM)
        #                 channel_totals[colnum] = (channel_totals[colnum] + sales_value) if channel_totals and colnum in channel_totals else sales_value
        #                 year_total += sales_value
        #                 colnum += 1
        #             sheet.write(rownum, colnum, year_total if year_total else '', NORM_NUM)
        #             channel_totals[colnum] = (channel_totals[colnum] + year_total) if channel_totals and colnum in channel_totals else year_total
        #             line_total += year_total
        #             colnum += 1
        #         sheet.write(rownum, colnum, line_total if line_total else '', NORM_NUM)
        #         channel_totals[colnum] = (channel_totals[colnum] + year_total) if channel_totals and colnum in channel_totals else year_total
        #         rownum += 1
        #     sheet.write(rownum, 0, str(channel) + ' Totals', BLU4_LFT)
        #     for col in range(colnum - 1):
        #         sheet.write(rownum, col + 2, channel_totals.get(col + 2) if channel_totals.get(col + 2) else '', BLU4_NUM)
        #     rownum += 1
        #OLD format
        HD_DBLUE_L = workbook.add_format({'bg_color': '#B4C6E7', 'align':'left', 'valign':'vcenter', 'text_wrap':True, 'font_name':'Calibri', 'border':1 })
        HD_DBLUE_L_BLD = workbook.add_format({'bg_color': '#B4C6E7', 'align':'left', 'valign':'vcenter', 'text_wrap':True, 'font_name':'Calibri', 'border':1,'bold':True})
        DBLUE_C_BLD_NUM = workbook.add_format({'bg_color': '#B4C6E7', 'align':'right', 'valign':'vcenter', 'text_wrap':True, 'font_name':'Calibri', 'num_format': '#,##0.00'})
        HD_DBLUE_C = workbook.add_format({'bg_color': '#B4C6E7', 'align':'center', 'valign':'vcenter', 'text_wrap':True, 'font_name':'Calibri', 'border':1 })
        NORM_NUM = workbook.add_format({'num_format': '#,##0.00'})
        LBLUE_NUM = workbook.add_format({'num_format': '#,##0.00', 'bg_color': '#DDEBF7'})
        LBLUE_TXT = workbook.add_format({'bg_color': '#DDEBF7'})
        sheet = workbook.add_worksheet('Trade Channel')
        tradechannels = list(set([data['trade_channel'] for data in rawdata if data['trade_channel']]))
        periods = list(set([data['date'].strftime('%Y-%m') for data in rawdata]))
        tradechannels.sort()
        periods.sort()
        sheet.set_row(1, 35)
        sheet.set_column(0, 1, 20)
        col_num = 0
        sheet.merge_range(0, col_num, 1, col_num, 'Trade Channel', HD_DBLUE_L)
        col_num += 1
        sheet.merge_range(0, col_num, 1, col_num, 'Customer Classification', HD_DBLUE_L)
        year_name = 0
        for period in periods:
            col_num += 1
            sheet.set_column(col_num, col_num, 15)
            date_obj = datetime.strptime(period, '%Y-%m')
            if year_name != date_obj.year:
                if year_name != 0:
                    sheet.merge_range(0, col_num, 1, col_num, str(year_name) + " Total", HD_DBLUE_C)
                    col_num += 1
                yr_col_start = col_num
                year_name = date_obj.year
            if yr_col_start == col_num:
                sheet.write(0, col_num, year_name, HD_DBLUE_C)
            else:
                sheet.merge_range(0, yr_col_start, 0, col_num, year_name, HD_DBLUE_C)
            sheet.write(1, col_num, date_obj.strftime('%b'), HD_DBLUE_C)
        col_num += 1
        sheet.merge_range(0, col_num, 1, col_num, str(year_name) + " Total", HD_DBLUE_C)
        col_num += 1
        sheet.merge_range(0, col_num, 1, col_num, "Grand Total", HD_DBLUE_C)
        rownum = 2
        tradechannels.sort()
        overall_total = {}
        for channel in tradechannels:
            cust_classes = list(set([data['customer_classification'] for data in rawdata if data['trade_channel'] == channel]))
            cust_classes.sort()
            channel_tot = {}
            for cls in cust_classes:
                sheet.write(rownum, 0, channel, HD_DBLUE_L)
                sheet.write(rownum, 1, cls, HD_DBLUE_L)
                col_num = 2
                year_name = None
                year_total = 0
                grand_total = 0
                for period in periods:
                    if year_name and year_name != datetime.strptime(period, '%Y-%m').year:
                        sheet.set_column(col_num, col_num, 15)
                        sheet.write(rownum, col_num, year_total,NORM_NUM)
                        col_num += 1
                        grand_total += year_total
                        year_total = 0
                    tot = sum([data['sales_value'] for data in rawdata if data['trade_channel'] == channel and data['customer_classification'] == cls and data['date'].strftime('%Y-%m') == period])
                    channel_tot[period] = (channel_tot.get(period) + tot) if channel_tot and channel_tot.get(period) else tot
                    year_total += tot
                    sheet.set_column(col_num, col_num, 15)
                    sheet.write(rownum, col_num, tot, NORM_NUM)
                    col_num += 1
                    year_name = datetime.strptime(period, '%Y-%m').year
                sheet.set_column(col_num, col_num, 15)
                sheet.write(rownum, col_num, year_total, NORM_NUM)
                col_num += 1
                grand_total += year_total
                sheet.set_column(col_num, col_num, 15)
                sheet.write(rownum, col_num, grand_total, NORM_NUM)
                rownum += 1
                col_num = 2
                year_total = 0
                grand_total = 0
                year_name = ''
            for period in periods:
                sheet.write(rownum, 0, str(channel) + ' Total', HD_DBLUE_L_BLD)
                sheet.write(rownum, 1, '', HD_DBLUE_L_BLD)
                date_obj = datetime.strptime(period, '%Y-%m')
                if year_name != date_obj.year:
                    if year_name:
                        sheet.write(rownum, col_num, year_total, LBLUE_NUM)
                        col_num += 1
                        grand_total += year_total
                        year_total = 0
                    year_name = date_obj.year
                overall_total[period] = (overall_total.get(period) + channel_tot.get(period)) if overall_total and overall_total.get(period) else channel_tot.get(period)
                sheet.write(rownum, col_num, channel_tot.get(period), LBLUE_NUM)
                year_total += channel_tot.get(period)
                col_num += 1
            sheet.write(rownum, col_num, year_total, LBLUE_NUM)
            col_num += 1
            grand_total += year_total
            sheet.write(rownum, col_num, grand_total, LBLUE_NUM)
            rownum +=1
        year_total = 0
        grand_total = 0
        year_name = ''
        sheet.write(rownum, 0, 'Grand Total', HD_DBLUE_L_BLD)
        sheet.write(rownum, 1, '', HD_DBLUE_L_BLD)
        col_num = 2
        for period in periods:
            date_obj = datetime.strptime(period, '%Y-%m')
            if year_name != date_obj.year:
                if year_name:
                    sheet.write(rownum, col_num, year_total, DBLUE_C_BLD_NUM)
                    col_num += 1
                    grand_total += year_total
                    year_total = 0
                year_name = date_obj.year
            sheet.write(rownum, col_num, overall_total.get(period), DBLUE_C_BLD_NUM)
            year_total += overall_total.get(period)
            col_num += 1
        sheet.write(rownum, col_num, year_total, DBLUE_C_BLD_NUM)
        col_num += 1
        grand_total += year_total
        sheet.write(rownum, col_num, grand_total, DBLUE_C_BLD_NUM)

        end_time = time.time()
        duration_detail = {'description' : 'Creating Trade Channel Sheet',
                           'time_taken' : end_time - start_time}
        return duration_detail

    def _create_ytd_rawdata_sheet(self, workbook, rawdata):
        start_time = time.time()
        sheet = workbook.add_worksheet('YTD Rawdata')

        #Header Part
        sheet.set_column(0, 0, 12)
        sheet.write(0, 0, 'Date')

        sheet.set_column(1, 1, 12)
        sheet.write(0, 1, 'Move Type')

        sheet.set_column(2, 2, 35)
        sheet.write(0, 2, 'Partner')

        sheet.set_column(3, 3, 15)
        sheet.write(0, 3, 'Ref No')

        sheet.set_column(4, 4, 35)
        sheet.write(0,4, 'Product')

        sheet.set_column(5, 7, 8)
        sheet.write(0,5, 'Qty')
        sheet.write(0,6, 'PCP')
        sheet.write(0,7, 'CTN')

        sheet.set_column(8, 10, 10)
        sheet.write(0,8, 'Sales Value')
        sheet.write(0,9, 'Cost Value')
        sheet.write(0,10, 'GP Value')

        sheet.set_column(11, 10, 20)
        sheet.write(0,11, 'Brand')
        sheet.write(0,12, 'Product Category')

        sheet.set_column(13, 13, 35)
        sheet.write(0,13, 'Delivery Address')

        sheet.set_column(14, 16, 25)
        sheet.write(0,14, 'Trade Channel')
        sheet.write(0,15, 'Customer Classification')
        sheet.write(0,16, 'Customer Sub Classification')

        sheet.set_column(17, 20, 20)
        sheet.write(0,17, 'Account Manager')
        sheet.write(0,18, 'Account Executive')
        sheet.write(0,19, 'Merchandiser')
        sheet.write(0,20, 'Sales Man')

        #Detail Part
        rownum = 1
        for data in rawdata:
            sheet.write(rownum, 0, data['date'].strftime('%Y-%m-%d'))
            sheet.write(rownum, 1, data['move_type'])
            sheet.write(rownum, 2, data['partner'])
            sheet.write(rownum, 3, data['invoice_ref'])
            sheet.write(rownum, 4, data['product'])
            sheet.write(rownum, 5, data['quantity'])
            sheet.write(rownum, 6, data['pcp'])
            sheet.write(rownum, 7, data['quantity_ctn'])
            sheet.write(rownum, 8, data['sales_value'])
            sheet.write(rownum, 9, data['cost_value'])
            sheet.write(rownum, 10, data['gp_value'])
            sheet.write(rownum, 11, data['brand'])
            sheet.write(rownum, 12, data['product_category'])
            sheet.write(rownum, 13, data['delivery_address'])
            sheet.write(rownum, 14, data['trade_channel'])
            sheet.write(rownum, 15, data['customer_classification'])
            sheet.write(rownum, 16, data['customer_sub_classification'])
            sheet.write(rownum, 17, data['account_manager'])
            sheet.write(rownum, 18, data['account_executive'])
            sheet.write(rownum, 19, data['merchandiser'])
            sheet.write(rownum, 20, data['van_salesman'])
            rownum += 1
        end_time = time.time()
        duration_detail = {'description' : 'Creating YTD Rawdata Sheet',
                           'time_taken' : end_time - start_time}
        return duration_detail

    def _create_profitability_rawdata_sheet(self, workbook, rawdata):
        start_time = time.time()
        sheet = workbook.add_worksheet('Profitability Rawdata')

        #Header Part
        sheet.set_column(0, 0, 12)
        sheet.write(0, 0, 'Date')

        sheet.set_column(1, 1, 12)
        sheet.write(0, 1, 'Move Type')

        sheet.set_column(2, 2, 35)
        sheet.write(0, 2, 'Partner')

        sheet.set_column(3, 3, 15)
        sheet.write(0, 3, 'Ref No')

        sheet.set_column(4, 4, 35)
        sheet.write(0,4, 'Product')

        sheet.set_column(5, 7, 8)
        sheet.write(0,5, 'Qty')
        sheet.write(0,6, 'PCP')
        sheet.write(0,7, 'CTN')

        sheet.set_column(8, 10, 10)
        sheet.write(0,8, 'Sales Value')
        sheet.write(0,9, 'Cost Value')
        sheet.write(0,10, 'GP Value')

        sheet.set_column(11, 10, 20)
        sheet.write(0,11, 'Brand')
        sheet.write(0,12, 'Product Category')

        sheet.set_column(13, 13, 35)
        sheet.write(0,13, 'Delivery Address')

        sheet.set_column(14, 16, 25)
        sheet.write(0,14, 'Trade Channel')
        sheet.write(0,15, 'Customer Classification')
        sheet.write(0,16, 'Customer Sub Classification')

        sheet.set_column(17, 20, 20)
        sheet.write(0,17, 'Account Manager')
        sheet.write(0,18, 'Account Executive')
        sheet.write(0,19, 'Merchandiser')
        sheet.write(0,20, 'Sales Man')

        #Detail Part
        rownum = 1
        for data in rawdata:
            sheet.write(rownum, 0, data['date'].strftime('%Y-%m-%d'))
            sheet.write(rownum, 1, data['move_type'])
            sheet.write(rownum, 2, data['partner'])
            sheet.write(rownum, 3, data['invoice_ref'])
            sheet.write(rownum, 4, data['product'])
            sheet.write(rownum, 5, data['quantity'])
            sheet.write(rownum, 6, data['pcp'])
            sheet.write(rownum, 7, data['quantity_ctn'])
            sheet.write(rownum, 8, data['sales_value'])
            sheet.write(rownum, 9, data['cost_value'])
            sheet.write(rownum, 10, data['gp_value'])
            sheet.write(rownum, 11, data['brand'])
            sheet.write(rownum, 12, data['product_category'])
            sheet.write(rownum, 13, data['delivery_address'])
            sheet.write(rownum, 14, data['trade_channel'])
            sheet.write(rownum, 15, data['customer_classification'])
            sheet.write(rownum, 16, data['customer_sub_classification'])
            sheet.write(rownum, 17, data['account_manager'])
            sheet.write(rownum, 18, data['account_executive'])
            sheet.write(rownum, 19, data['merchandiser'])
            sheet.write(rownum, 20, data['van_salesman'])
            rownum += 1
        end_time = time.time()
        duration_detail = {'description' : 'Creating Profitability Rawdata Sheet',
                           'time_taken' : end_time - start_time}
        return duration_detail

    def _get_ytd_rawdata(self, date_start, date_end):
        start_time = time.time()
        query = """
            SELECT p.name AS partner,
			mp.name as master_parent,
            prf.quantity,
            pt.name AS product,
            tc.name AS trade_channel,
            cc.name AS customer_classification,
            csc.name AS customer_sub_classification,
            amp.name AS account_manager,
            am.name AS invoice_ref,
            prf.date,
            prf.sales_value,
            prf.cost_value,
            prf.gp_value,
            pm.name AS brand,
            pc.complete_name AS product_category,
            rps.name AS delivery_address,
            rpae.name AS account_executive,
            rpmr.name AS merchandiser,
            rpvn.name AS van_salesman,
            prf.gp_value,
            prf.move_type,
            prf.pcp,
            prf.quantity_ctn FROM
                (SELECT a.partner_id as partner_id, 
                    SUM(CASE WHEN a.move_type = 'out_invoice' THEN a.quantity ELSE -a.quantity END) as quantity, 
                    a.product_id as product_id, 
                    rp.master_parent_id as master_parent_id,
                    rp.trade_channel as trade_channel,
                    rp.customer_sub_classification as customer_sub_classification,
                    rp.customer_classification as customer_classification, 
                    rp.account_manager_id as account_manager_id, 
                    a.move_id as move_id, 
                    a.date as date, 
                    SUM(CASE WHEN a.move_type = 'out_invoice' THEN a.credit ELSE -a.debit END) as sales_value, 
                    COALESCE(c.cost_value, 0) as cost_value,
                    SUM(CASE WHEN a.move_type = 'out_invoice' THEN a.credit ELSE -a.debit END) - COALESCE(c.cost_value, 0) as gp_value,
                    prt.brand as brand_id,
                    prt.categ_id as product_category,
                    am.partner_shipping_id as partner_shipping_id,
                    rp.account_excutive_id as account_excutive_id,
                    rp.merchandiser_id2 as marchandiser_id,
                    a.move_type as move_type,
                    ppl.pcp AS pcp,
                    SUM(CASE WHEN a.move_type = 'out_invoice' THEN a.quantity ELSE -a.quantity END)  / ppl.pcp as quantity_ctn
                FROM account_move_line AS a 
                INNER JOIN res_partner AS rp ON a.partner_id = rp.id
                INNER JOIN account_move AS am ON a.move_id = am.id
                INNER JOIN product_product AS prd ON a.product_id = prd.id
                INNER JOIN product_template AS prt ON prd.product_tmpl_id = prt.id
                LEFT JOIN (	
                    SELECT move_id, product_id, SUM(CASE WHEN move_type = 'out_invoice' THEN debit ELSE -credit END) AS cost_value
                    FROM account_move_line
                    WHERE account_id IN (SELECT id FROM account_account WHERE user_type_id = 17)
                    GROUP BY move_id, product_id
                ) AS c ON a.move_id = c.move_id AND a.product_id = c.product_id
                LEFT JOIN(
                   SELECT MAX(pp.qty) as pcp, pp.product_id as product_id
                   FROM product_packaging as pp
                   WHERE pp.product_id is not NULL
                   GROUP BY pp.product_id
                ) AS ppl ON a.product_id = ppl.product_id
                WHERE a.move_type IN ('out_refund', 'out_invoice') AND 
                a.parent_state = 'posted' AND 
                a.account_id IN (SELECT id FROM account_account WHERE user_type_id = 13) 
                AND a.date >= %s AND a.date <= %s AND rp.trade_channel != 5	 
                GROUP BY prt.brand, prt.categ_id, rp.customer_sub_classification, a.partner_id, am.partner_shipping_id, 
                a.product_id, rp.master_parent_id, rp.trade_channel, rp.customer_classification, rp.account_manager_id, 
                a.move_id, a.date, c.cost_value, a.move_type, rp.account_excutive_id, rp.merchandiser_id2, a.move_type, ppl.pcp) AS prf 
                INNER JOIN res_partner AS p ON prf.partner_id = p.id
                INNER JOIN product_product AS pp ON prf.product_id = pp.id
                INNER JOIN product_template AS pt ON pp.product_tmpl_id = pt.id
                LEFT JOIN trade_channel AS tc ON prf.trade_channel = tc.id 
                LEFT JOIN customer_classification AS cc ON prf.customer_classification = cc.id
                LEFT JOIN customer_sub_classification AS csc ON prf.customer_sub_classification = csc.id
                LEFT JOIN res_users AS ru ON prf.account_manager_id = ru.id 
                LEFT JOIN res_partner AS amp ON ru.partner_id = amp.id
                INNER JOIN account_move AS am ON prf.move_id = am.id
                LEFT JOIN product_manufacturer AS pm ON prf.brand_id = pm.id
                LEFT JOIN product_category AS pc ON prf.product_category = pc.id
                LEFT JOIN res_partner AS rps ON prf.partner_shipping_id = rps.id
                LEFT JOIN res_users AS ruae ON prf.account_excutive_id = ruae.id
                LEFT JOIN res_partner AS rpae ON ruae.partner_id = rpae.id
                LEFT JOIN res_users AS rumr ON prf.marchandiser_id = rumr.id
                LEFT JOIN res_partner AS rpmr ON rumr.partner_id = rpmr.id
                LEFT JOIN res_users AS ruvn ON rps.merchandiser_id2 = ruvn.id
                LEFT JOIN res_partner AS rpvn ON ruvn.partner_id = rpvn.id
				LEFT JOIN master_parent AS mp ON p.master_parent_id = mp.id
                """
        self.env.cr.execute(query, (date_start, date_end))
        result = self.env.cr.dictfetchall()
        end_time = time.time()
        duration_detail = {'description' : 'Fetching YTD Rawdata',
                           'time_taken' : end_time - start_time}
        return result, duration_detail

    def _get_profitability_rawdata(self, date_start, date_end):
        start_time = time.time()
        query = """
            SELECT p.name AS partner,
            mp.name as master_parent,
            prf.quantity,
            pt.name AS product,
            tc.name AS trade_channel,
            cc.name AS customer_classification,
            csc.name AS customer_sub_classification,
            amp.name AS account_manager,
            am.name AS invoice_ref,
            prf.date,
            prf.sales_value,
            prf.cost_value,
            prf.gp_value,
            pm.name AS brand,
            pc.complete_name AS product_category,
            rps.name AS delivery_address,
            rpae.name AS account_executive,
            rpmr.name AS merchandiser,
            rpvn.name AS van_salesman,
            prf.gp_value,
            prf.move_type,
            prf.pcp,
            prf.quantity_ctn FROM
                (SELECT a.partner_id as partner_id, 
                    SUM(CASE WHEN a.move_type = 'out_invoice' THEN a.quantity ELSE -a.quantity END) as quantity, 
                    a.product_id as product_id, 
                    rp.master_parent_id as master_parent_id,
                    rp.trade_channel as trade_channel,
                    rp.customer_sub_classification as customer_sub_classification,
                    rp.customer_classification as customer_classification, 
                    rp.account_manager_id as account_manager_id, 
                    a.move_id as move_id, 
                    a.date as date, 
                    SUM(CASE WHEN a.move_type = 'out_invoice' THEN a.credit ELSE -a.debit END) as sales_value, 
                    COALESCE(c.cost_value, 0) as cost_value,
                    SUM(CASE WHEN a.move_type = 'out_invoice' THEN a.credit ELSE -a.debit END) - COALESCE(c.cost_value, 0) as gp_value,
                    prt.brand as brand_id,
                    prt.categ_id as product_category,
                    am.partner_shipping_id as partner_shipping_id,
                    rp.account_excutive_id as account_excutive_id,
                    rp.merchandiser_id2 as marchandiser_id,
                    a.move_type as move_type,
                    ppl.pcp AS pcp,
                    SUM(CASE WHEN a.move_type = 'out_invoice' THEN a.quantity ELSE -a.quantity END)  / ppl.pcp as quantity_ctn
                FROM account_move_line AS a 
                INNER JOIN res_partner AS rp ON a.partner_id = rp.id
                INNER JOIN account_move AS am ON a.move_id = am.id
                INNER JOIN product_product AS prd ON a.product_id = prd.id
                INNER JOIN product_template AS prt ON prd.product_tmpl_id = prt.id
                LEFT JOIN (	
                    SELECT move_id, product_id, SUM(CASE WHEN move_type = 'out_invoice' THEN debit ELSE -credit END) AS cost_value
                    FROM account_move_line
                    WHERE account_id IN (SELECT id FROM account_account WHERE user_type_id = 17)
                    GROUP BY move_id, product_id
                ) AS c ON a.move_id = c.move_id AND a.product_id = c.product_id
                LEFT JOIN(
                   SELECT MAX(pp.qty) as pcp, pp.product_id as product_id
                   FROM product_packaging as pp
                   WHERE pp.product_id is not NULL
                   GROUP BY pp.product_id
                ) AS ppl ON a.product_id = ppl.product_id
                WHERE a.move_type IN ('out_refund', 'out_invoice') AND 
                a.parent_state = 'posted' AND 
                a.account_id IN (SELECT id FROM account_account WHERE user_type_id = 13) 
                AND a.date >= %s AND a.date <= %s		 
                GROUP BY prt.brand, prt.categ_id, rp.customer_sub_classification, a.partner_id, am.partner_shipping_id, 
                a.product_id, rp.master_parent_id, rp.trade_channel, rp.customer_classification, rp.account_manager_id, 
                a.move_id, a.date, c.cost_value, a.move_type, rp.account_excutive_id, rp.merchandiser_id2, a.move_type, ppl.pcp) AS prf 
                INNER JOIN res_partner AS p ON prf.partner_id = p.id
                INNER JOIN product_product AS pp ON prf.product_id = pp.id
                INNER JOIN product_template AS pt ON pp.product_tmpl_id = pt.id
                LEFT JOIN trade_channel AS tc ON prf.trade_channel = tc.id 
                LEFT JOIN customer_classification AS cc ON prf.customer_classification = cc.id
                LEFT JOIN customer_sub_classification AS csc ON prf.customer_sub_classification = csc.id
                LEFT JOIN res_users AS ru ON prf.account_manager_id = ru.id 
                LEFT JOIN res_partner AS amp ON ru.partner_id = amp.id
                INNER JOIN account_move AS am ON prf.move_id = am.id
                LEFT JOIN product_manufacturer AS pm ON prf.brand_id = pm.id
                LEFT JOIN product_category AS pc ON prf.product_category = pc.id
                LEFT JOIN res_partner AS rps ON prf.partner_shipping_id = rps.id
                LEFT JOIN res_users AS ruae ON prf.account_excutive_id = ruae.id
                LEFT JOIN res_partner AS rpae ON ruae.partner_id = rpae.id
                LEFT JOIN res_users AS rumr ON prf.marchandiser_id = rumr.id
                LEFT JOIN res_partner AS rpmr ON rumr.partner_id = rpmr.id
                LEFT JOIN res_users AS ruvn ON rps.merchandiser_id2 = ruvn.id
                LEFT JOIN res_partner AS rpvn ON ruvn.partner_id = rpvn.id
                LEFT JOIN master_parent AS mp ON p.master_parent_id = mp.id
                """
        self.env.cr.execute(query, (date_start, date_end))
        result = self.env.cr.dictfetchall()
        end_time = time.time()
        duration_detail = {'description': 'Fetching Raw Data',
                           'time_taken': end_time - start_time}
        return result, duration_detail

    def _create_query_details(self, workbook, duration_data,date_start, date_end):
        sheet = workbook.add_worksheet('Query Details')

        sheet.set_column(0, 1, 20)
        sheet.write(1, 0, 'Start Date: ')
        sheet.write(1, 1, date_start)
        sheet.write(2, 0, 'End Date: ')
        sheet.write(2, 1, date_end)

        rownum = 4
        sheet.write(rownum, 0, 'Task', )
        sheet.write(rownum, 1, 'Duration (Sec)')
        for rec in duration_data:
            rownum += 1
            sheet.write(rownum, 0, rec['description'])
            sheet.write(rownum, 1, round(rec['time_taken'],2))


