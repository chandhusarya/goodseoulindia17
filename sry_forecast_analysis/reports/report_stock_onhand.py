
# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
import logging
from collections import defaultdict
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SaryaStockOnhandReport(models.AbstractModel):
    _name = 'report.sry_forecast_analysis.stock_onhand_report'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, lines):
        company_ids = [self.env.company.id]
        if 'context' in data:
            company_ids = data['context']['allowed_company_ids']
        elif 'company_ids' in data:
            company_ids = data['company_ids']
        for company_id in company_ids:
            company = self.env['res.company'].browse([company_id])
            sheet = workbook.add_worksheet('SOH Detailed Report - ' + str(company.name))
            self._set_header(workbook, sheet, company_id)
            self._set_details(workbook, sheet, company_id)

    def _set_details(self, workbook, sheet, company_id):
        product_details = self._get_product_details(company_id)
        if not product_details:
            return

        stock_details = self._get_location_wise_stocks(company_id)
        stock_locations = self.env['sry.forecast.location'].search([('report', '=', 'soh'),('total','!=',True), ('company_id', '=', company_id)]).sorted('name').mapped('name')
        WHITE_LBG = workbook.add_format({'font_size': 11, 'bg_color': '#FFFFFF', 'font_color': '#000000', 'align': 'left','valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1})
        WHITE_CBG = workbook.add_format({'font_size': 11, 'bg_color': '#FFFFFF', 'font_color': '#000000', 'align': 'center','valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1})
        BLUE_LBG = workbook.add_format({'font_size': 11, 'bg_color': '#B4C6E7', 'font_color': '#000000', 'bold': True,'align': 'left','valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1})
        BLUE_CBG = workbook.add_format({'font_size': 11, 'bg_color': '#B4C6E7', 'font_color': '#000000', 'bold': True,'align': 'center','valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1})
        row_num = 3
        for product in product_details:
            overall_total_ctn = 0
            overall_total_puom = 0
            location_ctn_totals = {}
            location_puom_totals = {}
            expiry_dates = self._get_expiry_dates(stock_details, product['id'])
            for exp_date in expiry_dates:
                sheet.write(row_num, 0, product['brand'], WHITE_CBG)
                sheet.write(row_num, 1, product['item_code'], WHITE_CBG)
                sheet.write(row_num, 2, product['barcode'], WHITE_CBG)
                sheet.write(row_num, 3, product['item_description']['en_US'], WHITE_LBG)
                sheet.write(row_num, 4, product['category'], WHITE_CBG)
                sheet.write(row_num, 5, product['increment'], WHITE_CBG)
                sheet.write(row_num, 6, product['puom'], WHITE_CBG)
                #TOTALs
                ctn_total, puom_total = self._get_expiry_wise_stock(stock_details, product['id'], exp_date)
                sheet.write(row_num, 7, exp_date, WHITE_CBG)
                sheet.write(row_num, 8, puom_total , WHITE_CBG)
                sheet.write(row_num, 9, ctn_total, WHITE_CBG)

                sheet.write(row_num, 10, "", WHITE_CBG)

                overall_total_ctn += ctn_total
                overall_total_puom += puom_total

                col_num = 11
                for location in stock_locations:
                    puom = 0
                    ctn = 0
                    for stock in stock_details:
                        if stock['product_id'] == product['id'] and stock['expiration_date'] == exp_date and stock['location'] == location and not stock['istotal']:
                            puom = round(stock['puom_qty'], 2)
                            ctn = round(stock['ctn_qty'], 2)
                            break
                    if location_ctn_totals and location_ctn_totals.get(location):
                        total_ctn = location_ctn_totals.get(location) + ctn
                    else:
                        total_ctn = ctn
                    location_ctn_totals.update({location:total_ctn})

                    if location_puom_totals and location_puom_totals.get(location):
                        total_puom = location_puom_totals.get(location) + puom
                    else:
                        total_puom = puom
                    location_puom_totals.update({location: total_puom})
                    sheet.write(row_num, col_num, puom, WHITE_CBG)
                    sheet.write(row_num, col_num + 1, ctn, WHITE_CBG)
                    col_num += 2
                sheet.write(row_num, col_num, "", WHITE_CBG)
                sheet.write(row_num, col_num+ 1, "", WHITE_CBG)
                sheet.write(row_num, col_num+ 2, "", WHITE_CBG)
                sheet.write(row_num, col_num+ 3, "", WHITE_CBG)
                sheet.write(row_num, col_num+ 4, "", WHITE_CBG)
                sheet.write(row_num, col_num+ 5, "", WHITE_CBG)
                row_num += 1

            sheet.write(row_num, 0, product['brand'], BLUE_CBG)
            sheet.write(row_num, 1, product['item_code'], BLUE_CBG)
            sheet.write(row_num, 2, product['barcode'], BLUE_CBG)
            sheet.write(row_num, 3, product['item_description']['en_US'], BLUE_LBG)
            sheet.write(row_num, 4, product['category'], BLUE_CBG)
            sheet.write(row_num, 5, product['increment'], BLUE_CBG)
            sheet.write(row_num, 6, product['puom'], BLUE_CBG)
            sheet.write(row_num, 7, '', BLUE_CBG)
            sheet.write(row_num, 8, overall_total_puom, BLUE_CBG)
            sheet.write(row_num, 9, overall_total_ctn, BLUE_CBG)

            stock_availability_status = self._get_stock_availability_status(overall_total_ctn)
            if stock_availability_status == 'ZERO STOCK':
                sheet.write(row_num, 10, stock_availability_status, workbook.add_format({'font_size': 11, 'bg_color': '#C00000', 'font_color': '#000000', 'bold': True, 'align': 'center','valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1}))
            else:
                sheet.write(row_num, 10, stock_availability_status, BLUE_CBG)
            col_num = 11

            for location in stock_locations:
                sheet.write(row_num, col_num, location_puom_totals.get(location) or 0, BLUE_CBG)
                sheet.write(row_num, col_num + 1, location_ctn_totals.get(location) or 0, BLUE_CBG)
                col_num += 2

            eta_data = self._get_etas(product['id'], company_id)

            for eta in eta_data:
                sheet.write(row_num, col_num, eta['eta'], workbook.add_format({'font_size': 11, 'bg_color': '#B4C6E7', 'font_color': '#000000', 'bold': True,'align': 'left','valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'num_format': 'dd/mm/yyyy'}))
                sheet.write(row_num, col_num + 1, eta['qty'], BLUE_CBG)
                col_num += 2

            while col_num < 21:
                sheet.write(row_num, col_num, '', BLUE_CBG)
                col_num+=1
            row_num += 1

    def _set_header(self, workbook, sheet, company_id):
        GREY_HEADER = workbook.add_format({'font_size': 11, 'bg_color': '#D9D9D9', 'font_color': '#000000', 'bold': True, 'align': 'center','valign': 'vcenter', 'text_wrap': True, 'font_name': 'Calibri', 'border': 2})
        sheet.freeze_panes(3, 0)

        sheet.merge_range(0, 0, 0, 6, "PRODUCT DESCRIPTION", GREY_HEADER)

        sheet.set_column(0, 0, 13) #Brand Name
        sheet.merge_range(1, 0, 2, 0, "BRAND NAME", GREY_HEADER)

        sheet.set_column(1, 1, 17.5) #Item Code
        sheet.merge_range(1, 1, 2, 1, "ITEM CODE", GREY_HEADER)

        sheet.set_column(2, 2, 13) #Barcode
        sheet.merge_range(1, 2, 2, 2, "BARCODE", GREY_HEADER)

        sheet.set_column(3, 3, 68.5) #Item Description
        sheet.merge_range(1, 3, 2, 3, "ITEM DESCRIPTION", GREY_HEADER)

        sheet.set_column(4, 4, 10) #Product Category
        sheet.merge_range(1, 4, 2, 4, "PRODUCT CATEGORY", GREY_HEADER)

        sheet.set_column(5, 5, 6) #INCREMENT
        sheet.merge_range(1, 5, 2, 5, "INCREMENT", GREY_HEADER)

        sheet.set_column(6, 6, 10) #PUOM
        sheet.merge_range(1, 6, 2, 6, "PUOM", GREY_HEADER)

        sheet.set_column(7, 7, 10) #Expiration
        sheet.merge_range(0, 7, 2, 7, "Expiration Date", GREY_HEADER)
        col_num = 7

        #TOTAL
        location_sum = self.env['sry.forecast.location'].search([('report', '=', 'soh'), ('company_id', '=', company_id)])
        wh_locations = location_sum.filtered(lambda l: l.total).sorted('name').mapped('name')
        if wh_locations:
            col_num += 1
            sheet.merge_range(0, col_num, 1, col_num + 1, "TOTAL", GREY_HEADER)
            sheet.write(2, col_num, "Qty in PUOM", GREY_HEADER)
            col_num += 1
            sheet.write(2, col_num, "Qty in CARTON", GREY_HEADER)
            col_num += 1
            #STATUS
            sheet.set_column(col_num, col_num, 17.5)
            sheet.merge_range(0, col_num, 2, col_num, "STATUS", GREY_HEADER)

        #WAREHOUSE LOCATION
        location_stocks = location_sum.filtered(lambda l: not l.total).sorted('name').mapped('name')
        if location_stocks:
            col_num += 1
            if len(location_stocks) == 1:
                sheet.merge_range(0, col_num, 0, col_num + 1, "WAREHOUSE LOCATION", GREY_HEADER)
            else:
                wh_len = len(location_stocks)
                sheet.merge_range(0, col_num, 0, col_num + (wh_len * 2) - 1, "WAREHOUSE LOCATION", GREY_HEADER)
            for location in location_stocks:
                sheet.set_column(col_num, col_num, None, None, {'level': 1})
                sheet.merge_range(1, col_num, 1, col_num + 1, location, GREY_HEADER)
                sheet.write(2, col_num, "Qty in PUOM", GREY_HEADER)
                col_num += 1
                sheet.write(2, col_num, "Qty in CARTON", GREY_HEADER)
                col_num += 1

        # ETA1
        sheet.set_column(col_num, col_num, 15) #Date
        sheet.set_column(col_num + 1, col_num + 1, 6)  #Qty
        sheet.merge_range(0, col_num, 1, col_num + 1, "ETA1", GREY_HEADER)
        sheet.write(2, col_num, "Date", GREY_HEADER)
        col_num +=1
        sheet.write(2, col_num, "Qty", GREY_HEADER)

        # ETA2
        col_num +=1
        sheet.set_column(col_num, col_num, 15) #Date
        sheet.set_column(col_num + 1, col_num + 1, 6)  #Qty
        sheet.merge_range(0, col_num, 1, col_num + 1, "ETA2", GREY_HEADER)
        sheet.write(2, col_num, "Date", GREY_HEADER)
        col_num +=1
        sheet.write(2, col_num, "Qty", GREY_HEADER)

        # ETA3
        col_num +=1
        sheet.set_column(col_num, col_num, 15) #Date
        sheet.set_column(col_num + 1, col_num + 1, 6)  #Qty
        sheet.merge_range(0, col_num, 1, col_num + 1, "ETA3", GREY_HEADER)
        sheet.write(2, col_num, "Date", GREY_HEADER)
        col_num +=1
        sheet.write(2, col_num, "Qty", GREY_HEADER)

    def _get_location_wise_stocks(self, company_id):

        # query = """
        #     (SELECT q.product_id, f.name AS location, TO_CHAR(lt.expiration_date, 'dd/mm/yyyy') AS expiration_date, COALESCE(SUM(q.quantity),0) AS puom_qty,  COALESCE(SUM(q.quantity),0)/ ppl.pcp AS ctn_qty,False AS IsTotal
        #     FROM sry_forecast_location AS f
        #     LEFT JOIN sry_forecast_location_stock_location_rel AS fl ON f.id = fl.sry_forecast_location_id
        #     LEFT JOIN stock_location AS sl ON fl.stock_location_id = sl.id
        #     LEFT JOIN stock_quant AS q ON fl.stock_location_id = q.location_id
        #     LEFT JOIN stock_lot AS lt ON q.lot_id = lt.id
        #     LEFT JOIN (SELECT MAX(pp.qty) as pcp, pp.product_id as product_id
        #             FROM product_packaging as pp
        #             WHERE pp.product_id is not NULL
        #             GROUP BY pp.product_id) AS ppl ON q.product_id = ppl.product_id
        #     WHERE f.report = 'soh' AND f.total != true
        #     GROUP BY f.name, q.product_id, expiration_date, ppl.pcp)
        #     UNION
        #     (SELECT q.product_id, '' AS location,TO_CHAR(lt.expiration_date, 'dd/mm/yyyy') AS expiration_date, COALESCE(SUM(q.quantity),0) AS puom_qty,  COALESCE(SUM(q.quantity),0)/ ppl.pcp AS ctn_qty,True AS IsTotal
        #     FROM sry_forecast_location AS f
        #     LEFT JOIN sry_forecast_location_stock_location_rel AS fl ON f.id = fl.sry_forecast_location_id
        #     LEFT JOIN stock_location AS sl ON fl.stock_location_id = sl.id
        #     LEFT JOIN stock_quant AS q ON fl.stock_location_id = q.location_id
        #     LEFT JOIN stock_lot AS lt ON q.lot_id = lt.id
        #     LEFT JOIN (SELECT MAX(pp.qty) as pcp, pp.product_id as product_id
        #                         FROM product_packaging as pp
        #                         WHERE pp.product_id is not NULL
        #                         GROUP BY pp.product_id) AS ppl ON q.product_id = ppl.product_id
        #     WHERE f.report = 'soh' AND f.total = true
        #     GROUP BY q.product_id, expiration_date, ppl.pcp)
        #     ORDER BY product_id, location, expiration_date
        # """


        #21/12/2023 Rigeesh: Above SQL changed to below SQL, after stock.locations has been changed.
        query = """
                    (SELECT s.product_id, f.name as location, TO_CHAR(lt.expiration_date, 'dd/mm/yyyy') AS expiration_date, COALESCE(SUM(s.puom_qty),0) AS puom_qty, COALESCE(SUM(s.puom_qty),0)/ ppl.pcp AS ctn_qty, False AS IsTotal
            FROM sry_forecast_location AS f
            LEFT JOIN sry_forecast_location_stock_location_rel AS fl ON f.id = fl.sry_forecast_location_id
            LEFT JOIN (
                SELECT sq.product_id, sq.lot_id, sl.location_id, COALESCE(SUM(sq.quantity),0) AS puom_qty
                FROM stock_location sl 
                LEFT JOIN stock_quant sq ON sq.location_id = sl.id
                WHERE sl.location_id not in (1,2,3,7)
                GROUP BY sq.product_id, sq.lot_id, sl.location_id
                ORDER BY sq.product_id, sq.lot_id, sl.location_id) AS s ON fl.stock_location_id = s.location_id
            LEFT JOIN stock_lot AS lt ON s.lot_id = lt.id
            LEFT JOIN (SELECT MAX(pp.qty) as pcp, pp.product_id as product_id
                        FROM product_packaging as pp
                        WHERE pp.product_id is not NULL
                        GROUP BY pp.product_id) AS ppl ON s.product_id = ppl.product_id
            WHERE report = 'soh' AND f.total != true AND f.company_id = %s
            GROUP BY s.product_id, f.name,TO_CHAR(lt.expiration_date, 'dd/mm/yyyy'),ppl.pcp)
            UNION
            (SELECT s.product_id, f.name as location, TO_CHAR(lt.expiration_date, 'dd/mm/yyyy') AS expiration_date, COALESCE(SUM(s.puom_qty),0) AS puom_qty, COALESCE(SUM(s.puom_qty),0)/ ppl.pcp AS ctn_qty, True AS IsTotal
            FROM sry_forecast_location AS f
            LEFT JOIN sry_forecast_location_stock_location_rel AS fl ON f.id = fl.sry_forecast_location_id
            LEFT JOIN (
                SELECT sq.product_id, sq.lot_id, sl.location_id, COALESCE(SUM(sq.quantity),0) AS puom_qty
                FROM stock_location sl 
                LEFT JOIN stock_quant sq ON sq.location_id = sl.id
                WHERE sl.location_id not in (1,2,3,7,23)
                GROUP BY sq.product_id, sq.lot_id, sl.location_id
                ORDER BY sq.product_id, sq.lot_id, sl.location_id) AS s ON fl.stock_location_id = s.location_id
            LEFT JOIN stock_lot AS lt ON s.lot_id = lt.id
            LEFT JOIN (SELECT MAX(pp.qty) as pcp, pp.product_id as product_id
                        FROM product_packaging as pp
                        WHERE pp.product_id is not NULL
                        GROUP BY pp.product_id) AS ppl ON s.product_id = ppl.product_id
            WHERE report = 'soh' AND f.total = true AND f.company_id = %s
            GROUP BY s.product_id, f.name,TO_CHAR(lt.expiration_date, 'dd/mm/yyyy'),ppl.pcp)
        """
        params = [company_id, company_id]
        self.env.cr.execute(query, tuple(params))
        result = self.env.cr.dictfetchall()
        return result

    def _get_product_details(self, company_id):
        query = """
            SELECT pp.id, br.name AS brand, pt.default_code AS item_code,pp.barcode, pt.name AS item_description, pc.name AS category, MAX(pg.qty) AS increment, 
            UPPER(prg.name) AS puom
            FROM product_product AS pp 
            JOIN product_template AS pt ON pp.product_tmpl_id = pt.id
            LEFT JOIN product_manufacturer AS br ON pt.brand=br.id
            LEFT JOIN product_category AS pc ON pt.categ_id = pc.id
            LEFT JOIN (SELECT product_id, MAX(qty) AS qty FROM product_packaging GROUP BY product_id) AS pg ON pg.product_id = pp.id
            LEFT JOIN (SELECT product_id, name FROM product_packaging WHERE primary_unit = true) AS prg ON prg.product_id = pp.id
            WHERE pt.type='product' and pp.active != false AND 
            (pt.company_id = %s OR pt.company_id is Null)
            GROUP BY pp.id, br.name, pt.default_code, pt.name, pc.name, prg.name
            ORDER BY item_code
            """
        params = [company_id]
        self.env.cr.execute(query, tuple(params))
        result = self.env.cr.dictfetchall()
        return result
    def _get_expiry_dates(self, stock_details, product_id):
        expiry_dates =[]
        for rec in stock_details:
            if rec['product_id'] == product_id and rec['expiration_date'] not in expiry_dates:
                expiry_dates.append(rec['expiration_date'])
        return expiry_dates
    def _get_expiry_wise_stock(self, stock_details, product_id, exp_date):
        puom_total = 0
        ctn_total = 0
        for stock in stock_details:
            if stock['product_id'] == product_id and stock['expiration_date'] == exp_date and stock['istotal']:
                puom_total += stock['puom_qty']
                ctn_total += stock['ctn_qty']
        return round(ctn_total,2), round(puom_total,2)
    def _get_stock_availability_status(self,overall_total_ctn):
        result = ""
        if overall_total_ctn <= 5:
            result = 'ZERO STOCK'
        elif 5 < overall_total_ctn <= 25:
            result = 'LESS THAN 25 CTN'
        elif 25 < overall_total_ctn <= 50:
            result = 'LESS THAN 50 CTN'
        elif 50 < overall_total_ctn <= 100:
            result = 'LESS THAN 100 CTN'
        return result


    def _get_etas(self, product_id, company_id):
        final_rec = []

        expiry_count = 0
        bl_mapping = {}
        po_mapping = {}

        #Read Data from shipment advice if any
        query = """
            SELECT ship_adv.name as name, po_line.product_id, alloc.shipment_advice_line_qty, 
            po_line.product_id as product_id, ship_adv.expected_date, 
            ship_adv.bl_entry_id, po_line.id as po_line, po.id as po
            FROM lpo_wise_shipment_allocation as alloc
            JOIN shipment_advice as ship_adv on ship_adv.id = alloc.shipment_advice_id
            JOIN purchase_order_line as po_line on po_line.id = alloc.purchase_line_id
            JOIN purchase_order as po on po.id = po_line.order_id
            WHERE ship_adv.state not in ('done', 'item_in_receiving', 'item_received', 'cancel')  AND 
            po_line.product_id = %s AND ship_adv.company_id = %s
        """
        params = [product_id, company_id]
        self.env.cr.execute(query, tuple(params))
        shipment_advice_datas = self.env.cr.dictfetchall()
        for data in shipment_advice_datas:

            if data['expected_date'] and data['shipment_advice_line_qty']:
                final_rec.append({
                    'ref': data['name'],
                    'eta': data['expected_date'],
                    'qty': data['shipment_advice_line_qty'],
                })

                if data['bl_entry_id'] in bl_mapping:

                    bl_mapping[data['bl_entry_id']] += data['shipment_advice_line_qty']
                else:
                    bl_mapping[data['bl_entry_id']] = data['shipment_advice_line_qty']
                expiry_count += 1

        #check in BL entry

        query = '''
            SELECT sum(bl_l.bl_qty) as bl_qty, bl.expected_date, po.id as po_id, bl.id as bl_id
            FROM bl_entry_lines AS bl_l
            JOIN bl_entry AS bl ON bl.id = bl_l.bl_entry_id
            LEFT JOIN bl_entry_line_purchase_order as mm_blpo on bl_l.id = mm_blpo.bl_entry_line_id
            LEFT JOIN purchase_order as po on po.id = mm_blpo.purchase_id
            WHERE bl_l.product_id = %s and bl.state != 'close' and bl.company_id = %s
            GROUP BY bl.expected_date, po.id, bl.id
        '''

        params = [product_id, company_id]
        self.env.cr.execute(query, tuple(params))
        bl_datas = self.env.cr.dictfetchall()

        for data in bl_datas:
            bl_id = data['bl_id']
            bl_qty = data['bl_qty']
            expected_date = data['expected_date']
            po_id = data['po_id']

            query_shipment = '''
                SELECT SUM(alloc.shipment_advice_line_qty) as shipment_advice_line_qty
                FROM lpo_wise_shipment_allocation AS alloc
                JOIN shipment_advice AS ship_adv ON ship_adv.id = alloc.shipment_advice_id
                JOIN purchase_order_line AS po_line ON po_line.id = alloc.purchase_line_id
                WHERE po_line.product_id = %s and ship_adv.bl_entry_id = %s
            '''
            params_shipment = [product_id, bl_id]
            self.env.cr.execute(query_shipment, tuple(params_shipment))
            shipment_data = self.env.cr.dictfetchall()

            shipment_advice_line_qty = 0
            if shipment_data and shipment_data[0]['shipment_advice_line_qty']:
                shipment_advice_line_qty = shipment_data[0]['shipment_advice_line_qty']

            remaining_bl_qty = bl_qty - shipment_advice_line_qty

            if remaining_bl_qty > 0 and expected_date:
                final_rec.append({
                    'ref': 'bl',
                    'eta': expected_date,
                    'qty': remaining_bl_qty,
                })

                expiry_count += 1

            #any bl contains shipment advice qty and bl qty. So consider only bl qty
            #and we can have decduct from remaining po qty
            if po_id in po_mapping:
                po_mapping[po_id] += bl_qty
            else:
                po_mapping[po_id] = bl_qty


        #Read expiry from PO
        query = '''
            SELECT pol.product_id, 
                po.id as po_id,
                po.name AS po_name, 
                po.estimated_arrival_date AS po_eta, 
                pol.product_packaging_qty AS po_qty, 
                prd_pkg.qty as product_pkg_qty,
                pol.product_qty AS po_product_qty,
                pol.qty_received AS po_qty_received
                
                FROM purchase_order_line AS pol 
                JOIN purchase_order AS po ON pol.order_id = po.id
                JOIN product_packaging AS prd_pkg ON pol.product_packaging_id = prd_pkg.id
                
                
                WHERE po.state = 'purchase' AND po.is_closed != True AND pol.product_id = %s
                AND po.estimated_arrival_date >= CURRENT_DATE AND po.company_id=%s
                GROUP BY pol.product_id, po.name, 
                po_eta, pol.product_packaging_qty, 
                pol.qty_received, pol.product_qty, prd_pkg.qty, po.id 
                ORDER BY pol.product_id, po.estimated_arrival_date DESC
        '''

        params = [product_id, company_id]
        self.env.cr.execute(query, tuple(params))
        po_datas = self.env.cr.dictfetchall()

        for data in po_datas:

            po_product_qty = data['po_product_qty']
            product_pkg_qty = data['product_pkg_qty']
            po_eta = data['po_eta']
            po_id = data['po_id']


            po_product_qty = po_product_qty / product_pkg_qty

            #Check same item is ready captured on bl entry
            bl_qty = po_mapping.get(po_id, 0)
            if bl_qty > 0:
                po_product_qty = po_product_qty - bl_qty

            if po_product_qty > 0 and data['po_eta']:
                final_rec.append({
                    'ref': data['po_name'],
                    'eta': data['po_eta'],
                    'qty': po_product_qty,
                })

        sums = defaultdict(float)
        for item in final_rec:
            eta = item['eta'] + relativedelta(days=10)
            qty = item['qty']
            sums[eta] += qty
        # Convert the result back to a list of dictionaries
        result = [{'eta': eta, 'qty': total} for eta, total in sums.items()]
        result = sorted(result, key=lambda x: x['eta'])
        return result

