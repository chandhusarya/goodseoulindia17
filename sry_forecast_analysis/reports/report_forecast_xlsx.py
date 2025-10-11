
# -*- coding: utf-8 -*-
import datetime
import time

from odoo import models, fields, api,_
import logging
_logger = logging.getLogger(__name__)
from dateutil.relativedelta import relativedelta

class ForecastAnalysisReport(models.AbstractModel):
    _name = 'report.sry_forecast_analysis.forecast_analysis_report'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, lines):
        sheet = workbook.add_worksheet('Trend Analysis & Forecast')
        self._set_header(workbook, sheet, data['cols'], data['month_full'],
                         data['month_short'], data['wh_locations'], data['max_number_of_eta'])
        self._set_details(workbook, sheet, data)

    def _set_header(self,workbook,sheet, cols, month_full, month_short, wh_locations, max_number_of_eta):
        #Formats
        VIOLET_HEADER = workbook.add_format({'font_size': 11, 'bg_color': '#D9E1F2', 'font_color':'#000000','bold':True,'align':'center', 'valign':'vcenter','text_wrap':True,'font_name':'Calibri','border':2})
        GREEN_HEADER = workbook.add_format({'font_size': 11, 'bg_color': '#70AD47', 'font_color': '#000000', 'bold': True, 'align': 'center','valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 2})
        LIGHT_ORANGE_HEADER = workbook.add_format({'font_size': 11, 'bg_color': '#FCE4D6', 'font_color': '#000000', 'bold': True, 'align': 'center','valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 2})
        ORANGE_HEADER = workbook.add_format({'font_size': 11, 'bg_color': '#ED7D31', 'font_color': '#000000', 'bold': True, 'align': 'center','valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 2})
        LIGHT_GREEN_HEADER = workbook.add_format({'font_size': 11, 'bg_color': '#E2EFDA', 'font_color': '#000000', 'bold': True, 'align': 'center','valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 2})
        GREY_HEADER = workbook.add_format({'font_size': 11, 'bg_color': '#BFBFBF', 'font_color': '#000000', 'bold': True, 'align': 'center','valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 2})
        DARK_GREY_HEADER = workbook.add_format({'font_size': 11, 'bg_color': '#595959', 'font_color': '#FFFFFF', 'bold': True, 'align': 'center','valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 2})
        WHITE_HEADER = workbook.add_format({'font_size': 11, 'bg_color': 'white', 'font_color': '#000000', 'bold': True, 'align': 'center','valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 2})
        DARK_YELLOW_HEADER = workbook.add_format({'font_size': 11, 'bg_color': '#FFC000', 'font_color':'#000000','bold':True,'align':'center', 'valign':'vcenter','text_wrap':True,'font_name':'Calibri','border':2})
        YELLOW_HEADER = workbook.add_format({'font_size': 11, 'bg_color': '#FFE699', 'font_color':'#000000','bold':True,'align':'center', 'valign':'vcenter','text_wrap':True,'font_name':'Calibri','border':2})
        BLUE_HEADER = workbook.add_format({'font_size': 11, 'bg_color': '#8EA9DB', 'font_color':'#000000','bold':True,'align':'center', 'valign':'vcenter','text_wrap':True,'font_name':'Calibri','border':2})
        DARK_BLUE_HEADER = workbook.add_format({'font_size': 11, 'bg_color': '#203764', 'font_color': '#FFFFFF', 'bold': True, 'align': 'center','valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 2})
        LIGHT_BLUE_HEADER = workbook.add_format({'font_size': 11, 'bg_color': '#D9E1F2', 'font_color':'#000000','bold':True,'align':'center', 'valign':'vcenter','text_wrap':True,'font_name':'Calibri','border':2})
        BLACK_HEADER = workbook.add_format({'font_size': 11, 'bg_color': '#222B35', 'font_color': '#FFFFFF', 'bold': True, 'align': 'center','valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 2})

        sheet.freeze_panes(8, 0)

        # Widths
        sheet.set_column(0, 0, 10) #Brand Name
        sheet.set_column(1, 1, 11.5) #Product Category
        sheet.set_column(2, 2, 17.5) #Item Code
        sheet.set_column(3, 3, 68.5) #Item Description
        sheet.set_column(4, 4, 10) #FIRST SHIPMENT RECEIPT DATE
        sheet.set_column(5, 5, 12) #PCB
        sheet.set_column(6, 6, 11) #UOM
        sheet.set_column(7, 7, 10) #Shelf Days

        #Report Date
        sheet.write(0, 0, "DATE",workbook.add_format({'font_size': 11, 'bg_color': '#000000', 'font_color':'#FFFFFF'}))
        today = datetime.datetime.today().strftime('%d/%m/%Y')
        sheet.write(0, 1, today, workbook.add_format({'font_size': 11, 'bg_color': '#000000', 'font_color':'#FFFFFF'}))

        sheet.merge_range(2, 0, 7, 0, "Brand Name", VIOLET_HEADER)
        sheet.merge_range(2, 1, 7, 1, "Product Category", VIOLET_HEADER)
        sheet.merge_range(2, 2, 7, 2, "Item Code", VIOLET_HEADER)
        sheet.merge_range(2, 3, 7, 3, "Item Description", VIOLET_HEADER)
        sheet.merge_range(2, 4, 7, 4, "First Invoice Date", VIOLET_HEADER)
        sheet.merge_range(2, 5, 7, 5, "PCB", VIOLET_HEADER)
        sheet.merge_range(2, 6, 7, 6, "UOM", VIOLET_HEADER)
        sheet.merge_range(2, 7, 7, 7, "SHELF DAYS", VIOLET_HEADER)
        for col in range(cols):
            col_length = col * 60
            if col == cols - 1:
                sheet.merge_range(2, 8 + col_length, 4, 9 + col_length, "PREV MNTH AVG ACTL", LIGHT_BLUE_HEADER)
                sheet.merge_range(5, 8 + col_length, 7, 8 + col_length, "Current Year", LIGHT_BLUE_HEADER)
                sheet.merge_range(5, 9 + col_length, 7, 9 + col_length, "Previous Year", LIGHT_BLUE_HEADER)
                #sheet.merge_range(2, 10 + col_length, 7, 10 + col_length, "NEXT MNTH AVG ACTL", LIGHT_BLUE_HEADER)
                sheet.merge_range(2, 10 + col_length, 7, 10 + col_length, "NEXT 3 MONTHS AVERAGE (BUDGETED)", LIGHT_BLUE_HEADER)
                col_length += 3

            sheet.merge_range(2, 8 + col_length, 2, col_length + 67, month_full[col], VIOLET_HEADER)
            for col_num in range(60):
                sheet.write(3, 8 + col_length + col_num, month_short[col], VIOLET_HEADER)
            sheet.merge_range(4, 8 + col_length, 4, 8 + col_length + 3,  "Near Expiry Liquidation", GREEN_HEADER)
            sheet.merge_range(5, 8 + col_length, 7, 8 + col_length, "Previous Year", LIGHT_GREEN_HEADER)
            sheet.merge_range(5, 9 + col_length, 7, 9 + col_length, "Current Year", LIGHT_GREEN_HEADER)
            sheet.merge_range(5, 10 + col_length, 5, 10 + col_length + 1, "Year over Year", GREY_HEADER)
            sheet.merge_range(6, 10 + col_length, 7, 10 + col_length, "Quantity", GREY_HEADER)
            sheet.merge_range(6, 11 + col_length, 7, 11 + col_length, "%", GREY_HEADER)

            sheet.merge_range(4, 12 + col_length, 4, 12 + col_length + 15, "Promotion", ORANGE_HEADER)
            sheet.merge_range(5, 12 + col_length, 5, 12 + col_length + 5, "Previous Year", LIGHT_ORANGE_HEADER)
            sheet.write(6, 12 + col_length, "Budgeted", WHITE_HEADER)
            sheet.write(7, 12 + col_length, "Total", WHITE_HEADER)
            sheet.merge_range(6, 13 + col_length,6, 13 + col_length + 2, "Actual",LIGHT_ORANGE_HEADER)
            sheet.write(7, 13 + col_length, "Price Off",LIGHT_ORANGE_HEADER)
            sheet.write(7, 14 + col_length, "Price Comp",LIGHT_ORANGE_HEADER)
            sheet.write(7, 15 + col_length, "Total", WHITE_HEADER)
            sheet.merge_range(6, 16 + col_length, 6, 16 + col_length + 1,"Variance", GREY_HEADER)
            sheet.write(7, 16 + col_length, "Quantity", GREY_HEADER)
            sheet.write(7, 17 + col_length, "%", GREY_HEADER)
            sheet.merge_range(5, 18 + col_length, 5, 18 + col_length + 5, "Current Year", LIGHT_ORANGE_HEADER)
            sheet.write(6, 18 + col_length, "Budgeted", WHITE_HEADER)
            sheet.write(7, 18 + col_length, "Total", WHITE_HEADER)
            sheet.merge_range(6, 19 + col_length, 6, 19 + col_length + 2, "Actual", LIGHT_ORANGE_HEADER)
            sheet.write(7, 19 + col_length, "Price Off", LIGHT_ORANGE_HEADER)
            sheet.write(7, 20 + col_length, "Price Comp", LIGHT_ORANGE_HEADER)
            sheet.write(7, 21 + col_length, "Total", LIGHT_ORANGE_HEADER)
            sheet.merge_range(6, 22 + col_length, 6, 22 + col_length + 1, "Variance", GREY_HEADER)
            sheet.write(7, 22 + col_length, "Quantity", GREY_HEADER)
            sheet.write(7, 23 + col_length, "%", GREY_HEADER)
            sheet.merge_range(5, 24 + col_length, 5, 24 + col_length + 3, "Year Over Year", GREY_HEADER)
            sheet.merge_range(6, 24 + col_length, 6, 24 + col_length + 1, "Budgeted", GREY_HEADER)
            sheet.write(7, 24 + col_length, "Quantity", GREY_HEADER)
            sheet.write(7, 25 + col_length, "%", GREY_HEADER)
            sheet.merge_range(6, 26 + col_length, 6, 26 + col_length + 1, "Actual", GREY_HEADER)
            sheet.write(7, 26 + col_length, "Quantity", GREY_HEADER)
            sheet.write(7, 27 + col_length, "%", GREY_HEADER)

            sheet.merge_range(4, 28 + col_length, 4, 28 + col_length + 27, "Regular Sales", DARK_YELLOW_HEADER)
            sheet.merge_range(5, 28 + col_length, 5, 28 + col_length + 11, "Previous Year", YELLOW_HEADER)
            sheet.merge_range(6, 28 + col_length, 6, 28 + col_length + 4, "Budgeted", WHITE_HEADER)
            sheet.write(7, 28 + col_length, "Export", WHITE_HEADER)
            sheet.write(7, 29 + col_length, "Food Service", WHITE_HEADER)
            sheet.write(7, 30 + col_length, "Retail", WHITE_HEADER)
            sheet.write(7, 31 + col_length, "Whole Sale", WHITE_HEADER)
            sheet.write(7, 32 + col_length, "Total", WHITE_HEADER)
            sheet.merge_range(6, 33 + col_length, 6, 33 + col_length + 4, "Actual", YELLOW_HEADER)
            sheet.write(7 , 33 + col_length, "Export", WHITE_HEADER)
            sheet.write(7, 34 + col_length, "Food Service", WHITE_HEADER)
            sheet.write(7, 35 + col_length, "Retail", WHITE_HEADER)
            sheet.write(7, 36 + col_length, "Whole Sale", WHITE_HEADER)
            sheet.write(7, 37 + col_length, "Total", WHITE_HEADER)
            sheet.merge_range(6, 38 + col_length, 6, 38 + col_length + 1, "Variance", GREY_HEADER)
            sheet.write(7, 38 + col_length, "Quantity", GREY_HEADER)
            sheet.write(7, 39 + col_length, "%", GREY_HEADER)
            sheet.merge_range(5, 40 + col_length, 5, 40 + col_length + 11, "Current Year", YELLOW_HEADER)
            sheet.merge_range(6, 40 + col_length, 6, 40 + col_length + 4, "Budgeted", WHITE_HEADER)
            sheet.write(7, 40 + col_length, "Export", WHITE_HEADER)
            sheet.write(7, 41 + col_length, "Food Service", WHITE_HEADER)
            sheet.write(7, 42 + col_length, "Retail", WHITE_HEADER)
            sheet.write(7, 43 + col_length, "Whole Sale", WHITE_HEADER)
            sheet.write(7, 44 + col_length, "Total", WHITE_HEADER)
            sheet.merge_range(6, 45 + col_length, 6, 45 + col_length + 4,  "Actual", YELLOW_HEADER)
            sheet.write(7, 45 + col_length, "Export", WHITE_HEADER)
            sheet.write(7, 46 + col_length, "Food Service", WHITE_HEADER)
            sheet.write(7, 47 + col_length, "Retail", WHITE_HEADER)
            sheet.write(7, 48 + col_length, "Whole Sale", WHITE_HEADER)
            sheet.write(7, 49 + col_length, "Total", WHITE_HEADER)
            sheet.merge_range(6, 50 + col_length, 6, 50 + col_length + 1, "Variance", GREY_HEADER)
            sheet.write(7, 50 + col_length, "Quantity", GREY_HEADER)
            sheet.write(7, 51 + col_length, "%", GREY_HEADER)
            sheet.merge_range(5, 52 + col_length, 5, 52 + col_length + 3, "Year Over Year", GREY_HEADER)
            sheet.merge_range(6, 52 + col_length, 6, 52 + col_length + 1,  "Budgeted", GREY_HEADER)
            sheet.write(7, 52 + col_length, "Quantity", GREY_HEADER)
            sheet.write(7, 53 + col_length, "%", GREY_HEADER)
            sheet.merge_range(6, 54 + col_length, 6, 54 + col_length + 1, "Actual", GREY_HEADER)
            sheet.write(7, 54 + col_length, "Quantity", GREY_HEADER)
            sheet.write(7, 55 + col_length, "%", GREY_HEADER)

            sheet.merge_range(4, 56 + col_length, 4, 56 + col_length + 11, "TOTAL", BLUE_HEADER)
            sheet.merge_range(5, 56 + col_length, 5, 56 + col_length + 3, "Previous Year", LIGHT_BLUE_HEADER)
            sheet.write(6, 56 + col_length, "Budgeted", LIGHT_BLUE_HEADER)
            sheet.write(7, 56 + col_length, "Total", LIGHT_BLUE_HEADER)
            sheet.write(6, 57 + col_length, "Actual", LIGHT_BLUE_HEADER)
            sheet.write(7, 57 + col_length, "Total", LIGHT_BLUE_HEADER)
            sheet.merge_range(6, 58 + col_length, 6, 58 + col_length + 1, "Variance", GREY_HEADER)
            sheet.write(7, 58 + col_length, "Quantity", GREY_HEADER)
            sheet.write(7, 59 + col_length, "%", GREY_HEADER)
            sheet.merge_range(5, 60 + col_length, 5, 60 + col_length + 3, "Current Year", LIGHT_BLUE_HEADER)
            sheet.write(6, 60 + col_length, "Budgeted", LIGHT_BLUE_HEADER)
            sheet.write(7, 60 + col_length, "Total", LIGHT_BLUE_HEADER)
            sheet.write(6, 61 + col_length, "Actual", LIGHT_BLUE_HEADER)
            sheet.write(7, 61 + col_length, "Total", LIGHT_BLUE_HEADER)
            sheet.merge_range(6, 62 + col_length, 6, 62 + col_length + 1, "Variance", GREY_HEADER)
            sheet.write(7, 62 + col_length, "Quantity", GREY_HEADER)
            sheet.write(7, 63 + col_length, "%", GREY_HEADER)
            sheet.merge_range(5, 64 + col_length, 5, 64 + col_length + 3, "Year Over Year", GREY_HEADER)
            sheet.merge_range(6, 64 + col_length, 6, 64 + col_length + 1, "Budgeted", GREY_HEADER)
            sheet.write(7, 64 + col_length, "Quantity", GREY_HEADER)
            sheet.write(7, 65 + col_length, "%", GREY_HEADER)
            sheet.merge_range(6, 66 + col_length, 6, 66 + col_length + 1, "Actual", GREY_HEADER)
            sheet.write(7, 66 + col_length, "Quantity", GREY_HEADER)
            sheet.write(7, 67 + col_length, "%", GREY_HEADER)
        sheet.merge_range(2, 68 + col_length, 7, 68 + col_length, "EOM FORECAST", LIGHT_BLUE_HEADER)
        sheet.merge_range(2, 69 + col_length, 7, 69 + col_length, "Trend", LIGHT_BLUE_HEADER)
        col_length += 70
        if wh_locations:
            if len(wh_locations) == 1:
                sheet.write(2, col_length, "WAREHOUSE LOCATION", workbook.add_format({'font_size': 11, 'bg_color': 'white', 'font_color': '#000000', 'bold': True, 'align': 'center','valign': 'vcenter', 'font_name': 'Calibri', 'border': 2}))
            else:
                sheet.merge_range(2, col_length, 2, len(wh_locations) + col_length - 1, "WAREHOUSE LOCATION", WHITE_HEADER)
            for location in wh_locations:
                sheet.write(3, col_length, "", WHITE_HEADER)
                sheet.merge_range(4, col_length, 7, col_length, location, WHITE_HEADER)
                col_length += 1
        sheet.merge_range(2, col_length, 7, col_length, "TOTAL STOCK ON HAND", LIGHT_BLUE_HEADER)
        sheet.merge_range(2, 1 + col_length, 7, 1 + col_length, "AVERAGE SALES / MONTH", LIGHT_BLUE_HEADER)
        sheet.merge_range(2, 2 + col_length, 7, 2 + col_length, "SOH COVERAGE (MONTH)", LIGHT_BLUE_HEADER)
        sheet.merge_range(2, 3 + col_length, 7, 3 + col_length, "SOH COVERAGE (DAYS)", LIGHT_BLUE_HEADER)
        sheet.merge_range(2, 4 + col_length, 7, 4 + col_length, "ORDERING LEAD TIME (Days)", LIGHT_BLUE_HEADER)

        sheet.merge_range(2, 5 + col_length, 7, 5 + col_length, "NO OF DAYS TO BE OUT OF STOCK BEFORE NEW SHIPMENT", LIGHT_BLUE_HEADER)
        sheet.merge_range(2, 6 + col_length, 7, 6 + col_length, "SOH BALANCE BEFORE THE EXPECTED SHIPMENT", LIGHT_BLUE_HEADER)
        sheet.merge_range(2, 7 + col_length, 7, 7 + col_length, "SOH MONTH COVERAGE BEFORE THE NEW SHIPMENT", LIGHT_BLUE_HEADER)



        sheet.merge_range(2, 8 + col_length, 7, 8 + col_length, "ORDER REQUIRED - YES/NO", LIGHT_BLUE_HEADER)
        sheet.merge_range(2, 9 + col_length, 7, 9 + col_length, "Minimum Order Quantity (Supplier MOQ PUOM)", LIGHT_BLUE_HEADER)
        sheet.merge_range(2, 10 + col_length, 7, 10 + col_length, "Safety Stock", LIGHT_BLUE_HEADER)
        sheet.merge_range(2, 11 + col_length, 7, 11 + col_length, "Lead Time Demand", LIGHT_BLUE_HEADER)
        sheet.merge_range(2, 12 + col_length, 7, 12 + col_length, "FORECASTED QTY TO ORDER", LIGHT_BLUE_HEADER)
        sheet.merge_range(2, 13 + col_length, 2, 34 + col_length, "INVENTORY FORECASTING", DARK_GREY_HEADER)
        sheet.merge_range(3, 13 + col_length, 3, 24 + col_length, "SALES TEAM", YELLOW_HEADER)
        sheet.merge_range(4, 13 + col_length, 6, 17 + col_length, "FORECASTED QUANTITY", YELLOW_HEADER)
        sheet.merge_range(4, 18 + col_length, 6, 22 + col_length, "PROMOTIONAL/ADDITIONAL DEMAND", YELLOW_HEADER)
        sheet.write(7, 13 + col_length, "Export", DARK_YELLOW_HEADER)
        sheet.write(7, 14 + col_length, "Food Service", DARK_YELLOW_HEADER)
        sheet.write(7, 15 + col_length, "Retail", DARK_YELLOW_HEADER)
        sheet.write(7, 16 + col_length, "Wholesale", DARK_YELLOW_HEADER)
        sheet.write(7, 17 + col_length, "Total", DARK_YELLOW_HEADER)
        sheet.write(7, 18 + col_length, "Export", DARK_YELLOW_HEADER)
        sheet.write(7, 19 + col_length, "Food Service", DARK_YELLOW_HEADER)
        sheet.write(7, 20 + col_length, "Retail", DARK_YELLOW_HEADER)
        sheet.write(7, 21 + col_length, "Wholesale", DARK_YELLOW_HEADER)
        sheet.write(7, 22 + col_length, "Total", DARK_YELLOW_HEADER)
        sheet.merge_range(4, 23 + col_length, 7, 23 + col_length, "TOTAL QTY TO ORDER", DARK_YELLOW_HEADER)
        sheet.merge_range(4, 24 + col_length, 7, 24 + col_length, "Stock Coverage (Month)", DARK_YELLOW_HEADER)
        sheet.merge_range(3, 25 + col_length, 7, 25 + col_length, "TOTAL QTY TO ORDER IN CTN", DARK_BLUE_HEADER)


        current_col = 25 + col_length
        eta_start_col = current_col + 1

        for eta in range(max_number_of_eta):
            current_col = current_col + 1
            sheet.merge_range(6, current_col, 7, current_col, "ETA", BLACK_HEADER)
            sheet.set_column(current_col, current_col, 15)
            current_col = current_col + 1
            sheet.merge_range(6, current_col, 7, current_col, "QTY", BLACK_HEADER)

        current_col = current_col + 1
        sheet.merge_range(6, current_col, 7, current_col, "Remaining in Blanket Order", BLACK_HEADER)
        sheet.set_column(current_col, current_col, 15)  # width of Blanket Order Column

        #Setting header for ETA and QTY
        sheet.merge_range(3, eta_start_col, 5, current_col, "PENDING BALANCE QTY FROM SUPPLIER",
                              DARK_BLUE_HEADER)

        current_col = current_col + 1
        sheet.merge_range(3, current_col, 5, current_col+1, "Confirmed Ordered Qty", DARK_BLUE_HEADER)
        sheet.merge_range(6, current_col, 7, current_col, "PUOM", BLACK_HEADER)
        current_col = current_col + 1
        sheet.merge_range(6, current_col, 7, current_col, "CARTON", BLACK_HEADER)

        current_col = current_col + 1
        sheet.merge_range(3, current_col, 7, current_col, "ORDER DATE", BLACK_HEADER)

        current_col = current_col + 1
        sheet.merge_range(3, current_col, 7, current_col, "ETA", BLACK_HEADER)

        current_col = current_col + 1
        sheet.merge_range(3, current_col, 7,current_col, "Month Stock Coverage with the New ORDER at ETA", BLACK_HEADER)

        current_col = current_col + 1
        sheet.merge_range(3, current_col, 7, current_col, "FINAL ETA", BLACK_HEADER)

        current_col = current_col + 1
        sheet.merge_range(3, current_col, 7, current_col, "EXPIRY DATE", BLACK_HEADER)

        current_col = current_col + 1
        sheet.merge_range(3, current_col, 7, current_col, "REMAINING MONTH SHELF LIFE", BLACK_HEADER)

    def _set_details(self, workbook, sheet, data):
        BLUE_CDETAIL = workbook.add_format({'font_size': 11, 'bg_color': '#D9E1F2', 'font_color':'#000000','align':'right', 'valign':'vcenter','text_wrap':True,'font_name':'Calibri','border':1})
        RED_CDETAIL = workbook.add_format({'font_size': 11, 'bg_color': '#FF9797', 'font_color':'#000000','align':'right', 'valign':'vcenter','text_wrap':True,'font_name':'Calibri','border':1})
        GREEN_CDETAIL = workbook.add_format({'font_size': 11, 'bg_color': '#6FD783', 'font_color':'#000000','align':'right', 'valign':'vcenter','text_wrap':True,'font_name':'Calibri','border':1})
        GREY_CDETAIL = workbook.add_format({'font_size': 11, 'bg_color': '#BFBFBF', 'font_color': '#000000', 'align': 'right', 'valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1})
        LIGHT_ORANGE = workbook.add_format({'font_size': 11, 'bg_color': '#FCE4D6', 'font_color': '#000000', 'align': 'right','valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1})
        YELLOW_CFORMAT = workbook.add_format({'font_size': 11, 'bg_color': '#FFE699', 'font_color': '#000000','align':'right', 'valign':'vcenter','text_wrap':True,'font_name':'Calibri','border':1})
        DETAIL_LFORMAT = workbook.add_format({'font_size': 11, 'font_name': 'Calibri', 'valign':'vcenter','border': 1})
        DETAIL_RIGHT = workbook.add_format({'font_size': 11, 'font_name': 'Calibri', 'valign':'vcenter','border': 1, 'align': 'right'})
        DETAIL_CENTER = workbook.add_format({'font_size': 11, 'font_name': 'Calibri','valign':'vcenter', 'border': 1, 'align': 'center'})
        rows = data['rows']
        max_number_of_eta = data['max_number_of_eta']
        row_num = 8
        for row_item in rows:
            sheet.write(row_num, 0, row_item['brand'], DETAIL_LFORMAT)
            sheet.write(row_num, 1, row_item['category'], DETAIL_LFORMAT)
            sheet.write(row_num, 2, row_item['item_code'], DETAIL_LFORMAT)
            sheet.write(row_num, 3, row_item['item_name'], DETAIL_LFORMAT)
            sheet.write(row_num, 4, row_item['first_shipment_date'], DETAIL_CENTER)
            sheet.write(row_num, 5, row_item['pcb'], DETAIL_CENTER)
            sheet.write(row_num, 6, row_item['uom'], DETAIL_CENTER)
            sheet.write(row_num, 7, row_item['shelf_life'], DETAIL_CENTER)
            data_cols = data['cols']

            #Loop to Printing each month sales
            for col in range(data_cols):
                start_col = col * 60 + 8
                if col == data_cols-1:
                    sheet.write(row_num, 0 + start_col, row_item['prev_average_actual_curryr'], DETAIL_RIGHT)
                    sheet.write(row_num, 1 + start_col, row_item['prev_average_actual_prevyr'], DETAIL_RIGHT)
                    sheet.write(row_num, 2 + start_col, row_item['next_average_budget'], DETAIL_RIGHT)
                    start_col += 3
                sheet.write(row_num, 0 + start_col, row_item['nearexp_prevyear'][col], DETAIL_RIGHT)
                sheet.write(row_num, 1 + start_col, row_item['nearexp_curryear'][col], DETAIL_RIGHT)
                sheet.write(row_num, 2 + start_col, row_item['nearexp_yroveryr_qty'][col], GREY_CDETAIL)
                sheet.write(row_num, 3 + start_col, row_item['nearexp_yroveryr_perc'][col], GREY_CDETAIL)
                sheet.write(row_num, 4 + start_col, row_item['promo_prevyear_budg_total'][col], DETAIL_RIGHT)
                sheet.write(row_num, 5 + start_col, row_item['promo_prevyear_actual_priceoff'][col], LIGHT_ORANGE)
                sheet.write(row_num, 6 + start_col, row_item['promo_prevyear_actual_pricecomp'][col], LIGHT_ORANGE)
                sheet.write(row_num, 7 + start_col, row_item['promo_prevyear_actual_total'][col], DETAIL_RIGHT)
                sheet.write(row_num, 8 + start_col, row_item['promo_prevyear_variance_qty'][col], GREY_CDETAIL)
                sheet.write(row_num, 9 + start_col, row_item['promo_prevyear_variance_perc'][col], GREY_CDETAIL)
                sheet.write(row_num, 10 + start_col, row_item['promo_curryear_budg_total'][col], DETAIL_RIGHT)
                sheet.write(row_num, 11 + start_col, row_item['promo_curryear_actual_priceoff'][col], LIGHT_ORANGE)
                sheet.write(row_num, 12 + start_col, row_item['promo_curryear_actual_pricecomp'][col], LIGHT_ORANGE)
                sheet.write(row_num, 13 + start_col, row_item['promo_curryear_actual_total'][col], DETAIL_RIGHT)
                sheet.write(row_num, 14 + start_col, row_item['promo_curryear_variance_qty'][col], GREY_CDETAIL)
                sheet.write(row_num, 15 + start_col, row_item['promo_curryear_variance_perc'][col], GREY_CDETAIL)
                sheet.write(row_num, 16 + start_col, row_item['promo_yroveryr_budg_qty'][col], GREY_CDETAIL)
                sheet.write(row_num, 17 + start_col, row_item['promo_yroveryr_budg_perc'][col], GREY_CDETAIL)
                sheet.write(row_num, 18 + start_col, row_item['promo_yroveryr_actual_qty'][col], GREY_CDETAIL)
                sheet.write(row_num, 19 + start_col, row_item['promo_yroveryr_actual_perc'][col], GREY_CDETAIL)
                sheet.write(row_num, 20 + start_col, row_item['regular_prevyear_budg_export'][col], DETAIL_RIGHT)
                sheet.write(row_num, 21 + start_col, row_item['regular_prevyear_budg_foodservice'][col], DETAIL_RIGHT)
                sheet.write(row_num, 22 + start_col, row_item['regular_prevyear_budg_retail'][col], DETAIL_RIGHT)
                sheet.write(row_num, 23 + start_col, row_item['regular_prevyear_budg_wholesale'][col], DETAIL_RIGHT)
                sheet.write(row_num, 24 + start_col, row_item['regular_prevyear_budg_total'][col], DETAIL_RIGHT)
                sheet.write(row_num, 25 + start_col, row_item['regular_prevyear_actual_export'][col], DETAIL_RIGHT)
                sheet.write(row_num, 26 + start_col, row_item['regular_prevyear_actual_foodservice'][col], DETAIL_RIGHT)
                sheet.write(row_num, 27 + start_col, row_item['regular_prevyear_actual_retail'][col], DETAIL_RIGHT)
                sheet.write(row_num, 28 + start_col, row_item['regular_prevyear_actual_wholesale'][col], DETAIL_RIGHT)
                sheet.write(row_num, 29 + start_col, row_item['regular_prevyear_actual_total'][col], YELLOW_CFORMAT)
                sheet.write(row_num, 30 + start_col, row_item['regular_prevyear_variance_qty'][col], GREY_CDETAIL)
                sheet.write(row_num, 31 + start_col, row_item['regular_prevyear_variance_perc'][col], GREY_CDETAIL)
                sheet.write(row_num, 32 + start_col, row_item['regular_curryear_budg_export'][col], DETAIL_RIGHT)
                sheet.write(row_num, 33 + start_col, row_item['regular_curryear_budg_foodservice'][col], DETAIL_RIGHT)
                sheet.write(row_num, 34 + start_col, row_item['regular_curryear_budg_retail'][col], DETAIL_RIGHT)
                sheet.write(row_num, 35 + start_col, row_item['regular_curryear_budg_wholesale'][col], DETAIL_RIGHT)
                sheet.write(row_num, 36 + start_col, row_item['regular_curryear_budg_total'][col], DETAIL_RIGHT)
                sheet.write(row_num, 37 + start_col, row_item['regular_curryear_actual_export'][col], DETAIL_RIGHT)
                sheet.write(row_num, 38 + start_col, row_item['regular_curryear_actual_foodservice'][col], DETAIL_RIGHT)
                sheet.write(row_num, 39 + start_col, row_item['regular_curryear_actual_retail'][col], DETAIL_RIGHT)
                sheet.write(row_num, 40 + start_col, row_item['regular_curryear_actual_wholesale'][col], DETAIL_RIGHT)
                sheet.write(row_num, 41 + start_col, row_item['regular_curryear_actual_total'][col], YELLOW_CFORMAT)
                sheet.write(row_num, 42 + start_col, row_item['regular_curryear_variance_qty'][col], GREY_CDETAIL)
                sheet.write(row_num, 43 + start_col, row_item['regular_curryear_variance_perc'][col], GREY_CDETAIL)
                sheet.write(row_num, 44 + start_col, row_item['regular_yroveryr_budget_qty'][col],GREY_CDETAIL)
                sheet.write(row_num, 45 + start_col, row_item['regular_yroveryr_budget_perc'][col], GREY_CDETAIL)
                sheet.write(row_num, 46 + start_col, row_item['regular_yroveryr_actual_qty'][col], GREY_CDETAIL)
                sheet.write(row_num, 47 + start_col, row_item['regular_yroveryr_actual_perc'][col], GREY_CDETAIL)
                sheet.write(row_num, 48 + start_col, row_item['total_prevyear_budg_total'][col], DETAIL_RIGHT)
                sheet.write(row_num, 49 + start_col, row_item['total_prevyear_actual_total'][col], BLUE_CDETAIL)
                sheet.write(row_num, 50 + start_col, row_item['total_prevyear_variance_quantity'][col], GREY_CDETAIL)
                sheet.write(row_num, 51 + start_col, row_item['total_prevyear_variance_perc'][col], GREY_CDETAIL)
                sheet.write(row_num, 52 + start_col, row_item['total_curryear_budg_total'][col], DETAIL_RIGHT)
                sheet.write(row_num, 53 + start_col, row_item['total_curryear_actual_total'][col], BLUE_CDETAIL)
                sheet.write(row_num, 54 + start_col, row_item['total_curryear_variance_quantity'][col], GREY_CDETAIL)
                sheet.write(row_num, 55 + start_col, row_item['total_curryear_variance_perc'][col], GREY_CDETAIL)
                sheet.write(row_num, 56 + start_col, row_item['total_yroveryr_budg_quantity'][col], GREY_CDETAIL)
                sheet.write(row_num, 57 + start_col, row_item['total_yroveryr_budg_perc'][col], GREY_CDETAIL)
                sheet.write(row_num, 58 + start_col, row_item['total_yroveryr_actual_quantity'][col], GREY_CDETAIL)
                sheet.write(row_num, 59 + start_col, row_item['total_yroveryr_actual_perc'][col], GREY_CDETAIL)

            start_col += 60
            sheet.write(row_num, start_col, row_item['eom_forecast'], DETAIL_RIGHT)
            sheet.write(row_num, 1 + start_col, row_item['trend'], YELLOW_CFORMAT if row_item['trend'] == 'Upper Trend' else DETAIL_RIGHT)

            # Printing Warehouse locations
            start_col += 2
            for location in row_item['wh_locations']:
                onhand = 0
                for item in row_item['location_wise_stocks']:
                    if item['name'] == location:
                        onhand = item['onhand']
                        break
                sheet.write(row_num, start_col, round(onhand,1), DETAIL_RIGHT)
                start_col += 1

            sheet.write(row_num, start_col, row_item['total_stock_onhand'],BLUE_CDETAIL)
            sheet.write(row_num, 1 + start_col, row_item['average_sales_month'],BLUE_CDETAIL)

            #Conditional Formating for SOH Coverage
            if row_item['soh_coverage_month'] < 3:
                sheet.write(row_num, 2 + start_col, row_item['soh_coverage_month'], RED_CDETAIL)
            elif 3 <= row_item['soh_coverage_month'] < 6:
                sheet.write(row_num, 2 + start_col, row_item['soh_coverage_month'], YELLOW_CFORMAT)
            elif row_item['soh_coverage_month'] >= 6:
                sheet.write(row_num, 2 + start_col, row_item['soh_coverage_month'], GREEN_CDETAIL)

            sheet.write(row_num, 3 + start_col, row_item['soh_coverage_days'], DETAIL_RIGHT)
            sheet.write(row_num, 4 + start_col, row_item['ordering_lead_time'], DETAIL_RIGHT)

            sheet.write(row_num, 5 + start_col, row_item['no_stock_days_before_shipment'], RED_CDETAIL if row_item['no_stock_days_before_shipment'] > 1 else DETAIL_RIGHT)
            sheet.write(row_num, 6 + start_col, row_item['soh_bal_before_shipment'], RED_CDETAIL if row_item['soh_bal_before_shipment'] < 3 else DETAIL_RIGHT)

            sheet.write(row_num, 7 + start_col, row_item['soh_coverage_before_shipment'], RED_CDETAIL if row_item['soh_coverage_before_shipment'] < 3 else DETAIL_RIGHT)


            sheet.write(row_num, 8 + start_col, row_item['order_required'], DETAIL_CENTER)
            sheet.write(row_num, 9 + start_col, row_item['minimum_order_qty'], DETAIL_RIGHT)
            sheet.write(row_num, 10 + start_col, row_item['safety_stock'], DETAIL_RIGHT)
            sheet.write(row_num, 11 + start_col, row_item['lead_time_demand'], DETAIL_RIGHT)
            sheet.write(row_num, 12 + start_col, row_item['forecasted_qty_to_order'], DETAIL_RIGHT)
            sheet.write(row_num, 13 + start_col, row_item['inventory_forecast_qty_export'], BLUE_CDETAIL)
            sheet.write(row_num, 14 + start_col, row_item['inventory_forecast_qty_foodservice'], BLUE_CDETAIL)
            sheet.write(row_num, 15 + start_col, row_item['inventory_forecast_qty_retail'],BLUE_CDETAIL)
            sheet.write(row_num, 16 + start_col, row_item['inventory_forecast_qty_wholesale'],BLUE_CDETAIL)
            sheet.write(row_num, 17 + start_col, row_item['inventory_forecast_qty_total'],YELLOW_CFORMAT)
            sheet.write(row_num, 18 + start_col, "", BLUE_CDETAIL) #inventory_forecast_promo_export
            sheet.write(row_num, 19 + start_col, "", BLUE_CDETAIL) #inventory_forecast_promo_foodservice
            sheet.write(row_num, 20 + start_col, "", BLUE_CDETAIL) #inventory_forecast_promo_retail
            sheet.write(row_num, 21 + start_col, "", BLUE_CDETAIL) #inventory_forecast_promo_wholesale
            sheet.write(row_num, 22 + start_col, "", DETAIL_RIGHT) #inventory_forecast_promo_total
            sheet.write(row_num, 23 + start_col, "", BLUE_CDETAIL)  #inventory_total_qty_to_order
            sheet.write(row_num, 24 + start_col, "", DETAIL_RIGHT)#inventory_forecast_stock_coverage
            sheet.write(row_num, 25 + start_col, "", BLUE_CDETAIL) #inventory_total_qty_to_order_in_ctn

            #sheet.write(row_num, 26 + start_col, row_item['pending_balance_qty_from_supplier'], BLUE_CDETAIL)

            current_col = 25 + start_col
            eta_count = 0
            for eta in row_item['pending_qty_eta']:

                current_col = current_col + 1
                eta_data = eta['eta']
                sheet.write(row_num, current_col, eta_data, BLUE_CDETAIL)

                current_col = current_col + 1
                sheet.write(row_num, current_col, eta['qty'], BLUE_CDETAIL)

                eta_count = eta_count + 1

            #Need to fill in black columns to make eta upto longest eta count
            to_fill_columns = max_number_of_eta - eta_count
            for fill in range(to_fill_columns):
                current_col = current_col + 1
                sheet.write(row_num, current_col, "", BLUE_CDETAIL)
                current_col = current_col + 1
                sheet.write(row_num, current_col, "", BLUE_CDETAIL)



            current_col = current_col + 1
            sheet.write(row_num, current_col, row_item['remaining_qty_blanket_order'], BLUE_CDETAIL)  # inventory_forecast_confirmed_qty_puom

            current_col = current_col + 1
            sheet.write(row_num, current_col, "",BLUE_CDETAIL) #inventory_forecast_confirmed_qty_puom

            current_col = current_col + 1
            sheet.write(row_num, current_col, "",BLUE_CDETAIL) #inventory_forecast_confirmed_qty_carton

            current_col = current_col + 1
            sheet.write(row_num, current_col, "",DETAIL_RIGHT) #inventory_forecast_order_date

            current_col = current_col + 1
            sheet.write(row_num, current_col, "",DETAIL_RIGHT) #inventory_forecast_eta

            current_col = current_col + 1
            sheet.write(row_num, current_col, "",DETAIL_RIGHT) #inventory_forecast_month_stock_coverage

            current_col = current_col + 1
            sheet.write(row_num, current_col, "",DETAIL_RIGHT) #inventory_forecast_final_eta

            current_col = current_col + 1
            sheet.write(row_num, current_col, "",DETAIL_RIGHT) #inventory_forecast_expiry_date

            current_col = current_col + 1
            sheet.write(row_num, current_col, "",DETAIL_RIGHT) #inventory_forecast_remaining_month_shelf_life

            row_num += 1
