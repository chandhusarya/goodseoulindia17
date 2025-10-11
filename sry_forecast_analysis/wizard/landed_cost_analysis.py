from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from collections import OrderedDict
import io
from odoo.tools.misc import xlsxwriter

import base64

class landed_cost_analysis(models.TransientModel):
    _name = 'landed.cost.analysis'

    from_date = fields.Date("From Date")
    to_date = fields.Date("To Date")

    excel_file_name = fields.Char('Excel File Name')
    excel_file = fields.Binary("Excel File")

    def gen_landed_cost(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
        })

        sheet = workbook.add_worksheet("Analysis")

        sheet.set_column(0, 0, 10)
        sheet.set_column(1, 1, 10)
        sheet.set_column(2, 2, 24)
        sheet.set_column(3, 3, 15)
        sheet.set_column(4, 4, 16)
        sheet.set_column(5, 5, 15)
        sheet.set_column(6, 7, 50)
        sheet.set_column(7, 7, 10)
        sheet.set_column(8, 8, 10)
        sheet.set_column(9, 9, 10)
        sheet.set_column(14, 14, 12)#Total BD PD
        sheet.set_column(15, 15, 13)#In AED

        BOLD_NOBORDER = workbook.add_format({'bold': True, 'font_name': 'Calibri', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter'})
        SUM_FORMAT = workbook.add_format({'bold': True, 'font_name': 'Calibri', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter','top': 1, 'bottom': 6, 'num_format': '#,##0.00'})

        bl_list = self.find_eligible_bl()

        # Total variable Initialisation
        tot_qty_pcs = 0
        tot_qty_ctn = 0
        tot_pp_ad = 0
        tot_in_aed = 0
        tot_total_lc = 0
        tot_princ_disc = 0
        tot_contract_disc = 0
        tot_add_disc = 0
        total_lc = 0
        cost_names = self.env['product.product'].search([('landed_cost_ok', '=', True)]).mapped('name')

        # PRINT HEADERS
        row_num = 1
        col_num = 0
        sheet.write(row_num, col_num, "Currency\nRate", BOLD_NOBORDER)
        col_num = 1
        sheet.write(row_num, col_num, "Date", BOLD_NOBORDER)
        col_num += 1
        sheet.write(row_num, col_num, "BL", BOLD_NOBORDER)
        col_num += 1
        sheet.write(row_num, col_num, "Lot #", BOLD_NOBORDER)
        col_num += 1
        sheet.write(row_num, col_num, "Container #", BOLD_NOBORDER)
        col_num += 1
        sheet.write(row_num, col_num, "Product Code", BOLD_NOBORDER)
        col_num += 1
        sheet.write(row_num, col_num, "Product Name", BOLD_NOBORDER)
        col_num += 1
        sheet.write(row_num, col_num, "Qty Pcs", BOLD_NOBORDER)
        col_num += 1
        sheet.write(row_num, col_num, "Qty Recd", BOLD_NOBORDER)
        col_num += 1
        sheet.set_column(col_num, col_num, 13)
        sheet.write(row_num, col_num, "Principal Disc", BOLD_NOBORDER)
        col_num += 1
        sheet.set_column(col_num, col_num, 13)
        sheet.write(row_num, col_num, "Contractual Disc", BOLD_NOBORDER)
        col_num += 1
        sheet.set_column(col_num, col_num, 13)
        sheet.write(row_num, col_num, "Additional Disc", BOLD_NOBORDER)
        col_num += 1
        sheet.write(row_num, col_num, "AD Prices", BOLD_NOBORDER)
        col_num += 1
        sheet.write(row_num, col_num, "BD Prices", BOLD_NOBORDER)
        col_num += 1
        sheet.write(row_num, col_num, "Total PP AD", BOLD_NOBORDER)
        col_num += 1
        sheet.write(row_num, col_num, "In AED", BOLD_NOBORDER)
        #Printing Landed Costs Headers
        for cost in cost_names:
            col_num += 1
            sheet.set_column(col_num, col_num, 15)
            sheet.write(row_num, col_num, cost, BOLD_NOBORDER)
        col_num += 1
        sheet.set_column(col_num, col_num, 20)
        sheet.write(row_num, col_num, "Total LC", BOLD_NOBORDER)
        col_num += 1
        sheet.set_column(col_num, col_num, 8)
        sheet.write(row_num, col_num, "Conversion", BOLD_NOBORDER)
        col_num += 1
        sheet.write(row_num, col_num, "AD COGS CTN", BOLD_NOBORDER)
        col_num += 1
        sheet.write(row_num, col_num, "AD COGS PC", BOLD_NOBORDER)

        for bl in bl_list:
            currency_rate = self._get_currency_rate(bl)
            if not currency_rate:
                raise UserError(_("Currency Exchange rate is not available", (bl.name)))
            product_list = self._get_landed_cost_data(bl)

            #Printing Item Details.
            for product_info in product_list:
                row_num += 1
                col_num = 0
                sheet.write(row_num, col_num, currency_rate, workbook.add_format({'num_format': '#,##0.00'}))
                col_num += 1
                sheet.write(row_num, col_num, product_info['date'].strftime("%d/%m/%Y"))
                col_num += 1
                sheet.write(row_num, col_num, bl.name)
                col_num += 1
                sheet.write(row_num, col_num, product_info['lot'])
                col_num += 1
                sheet.write(row_num, col_num, product_info['container'])
                col_num += 1
                sheet.write(row_num, col_num, product_info['product_code'])
                col_num += 1
                sheet.write(row_num, col_num, product_info['product_name'])
                col_num += 1
                tot_qty_pcs += product_info['quantity']
                sheet.write(row_num, col_num, product_info['quantity'], workbook.add_format({'num_format': '#,##0.00'}))
                col_num += 1
                tot_qty_ctn += product_info['qty_rcvd']
                sheet.write(row_num, col_num, product_info['qty_rcvd'], workbook.add_format({'num_format': '#,##0.00'})) #Qty Rcvd
                col_num += 1

                # Column moved from end
                tot_princ_disc += product_info["principal_disc"]
                sheet.write(row_num, col_num, product_info["principal_disc"] or "", workbook.add_format({'num_format': '#,##0.00'}))
                col_num += 1
                tot_contract_disc += product_info["contractual_disc"]
                sheet.write(row_num, col_num, product_info["contractual_disc"] or "", workbook.add_format({'num_format': '#,##0.00'}))
                col_num += 1
                tot_add_disc +=  product_info["additional_disc"]
                sheet.write(row_num, col_num, product_info["additional_disc"] or "", workbook.add_format({'num_format': '#,##0.00'}))

                col_num += 1
                sheet.write(row_num, col_num, product_info["ad_price"], workbook.add_format({'num_format': '#,##0.00'})) #AD price
                col_num += 1
                sheet.write(row_num, col_num, product_info["bd_price"], workbook.add_format({'num_format': '#,##0.00'})) #BD price
                col_num += 1
                tot_pp_ad += product_info["pp_ad"]
                sheet.write(row_num, col_num, product_info["pp_ad"], workbook.add_format({'num_format': '#,##0.00'}))  # Total PP BD
                col_num += 1
                in_aed = currency_rate * (product_info["pp_ad"] if product_info["pp_ad"] else 0)
                tot_in_aed += in_aed
                sheet.write(row_num, col_num, in_aed, workbook.add_format({'num_format': '#,##0.00'}))
                total_lc = in_aed

                for cost in cost_names:
                    col_num += 1
                    sheet.write(row_num, col_num, product_info[cost] if cost in product_info else "", workbook.add_format({'num_format': '#,##0.00'}))
                    if cost in product_info:
                        total_lc += product_info[cost]
                col_num += 1
                tot_total_lc += total_lc
                sheet.write(row_num, col_num, total_lc, workbook.add_format({'num_format': '#,##0.00'}))
                col_num += 1
                sheet.write(row_num, col_num, product_info["conversion"] or "", workbook.add_format({'num_format': '#,##0.00'}))
                col_num += 1
                bd_cogs_ctn = total_lc / product_info['qty_rcvd']
                sheet.write(row_num, col_num, bd_cogs_ctn, workbook.add_format({'num_format': '#,##0.00'}))
                col_num += 1
                bd_cogs_pc = bd_cogs_ctn / product_info["conversion"]
                sheet.write(row_num, col_num, bd_cogs_pc or "", workbook.add_format({'num_format': '#,##0.00'}))
            # row_num += 3

        # Print bottom Totals
        row_num += 1
        col_num = 7
        if tot_qty_pcs: sheet.write(row_num, col_num, tot_qty_pcs or "", SUM_FORMAT)
        col_num += 1
        if tot_qty_ctn: sheet.write(row_num, col_num, tot_qty_ctn or "", SUM_FORMAT)
        col_num += 1
        if tot_princ_disc: sheet.write(row_num, col_num, tot_princ_disc or "", SUM_FORMAT)
        col_num += 1
        if tot_contract_disc: sheet.write(row_num, col_num, tot_contract_disc or "", SUM_FORMAT)
        col_num += 1
        if tot_add_disc: sheet.write(row_num, col_num, tot_add_disc or "", SUM_FORMAT)
        col_num += 3

        if tot_pp_ad: sheet.write(row_num, col_num, tot_pp_ad or "", SUM_FORMAT)
        col_num += 1
        if tot_in_aed: sheet.write(row_num, col_num, tot_in_aed or "", SUM_FORMAT)
        for cost in cost_names:
            col_num += 1
            cst = 0
            for bl in bl_list:
                product_list = self._get_landed_cost_data(bl)
                cst += sum(product_info.get(cost, 0) for product_info in product_list)
            sheet.write(row_num, col_num, cst, SUM_FORMAT)
        col_num += 1
        if tot_total_lc: sheet.write(row_num, col_num, tot_total_lc or "", SUM_FORMAT)
        col_num += 1

        workbook.close()
        output.seek(0)
        generated_file = base64.b64encode(output.read())
        output.close()

        self.excel_file = generated_file
        self.excel_file_name = "Landed Cost Detail Report.xlsx"

        return {
            'name': 'FEC',
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=landed.cost.analysis&id={}&field=excel_file&filename_field=excel_file_name&download=true'.format(self.id),
            'target': 'self',
        }

    def find_eligible_bl(self):
        bl_list = []
        shipment_advice = self.env['shipment.advice'].search([('arrival_date', '<=', self.to_date),
                                  ('arrival_date', '>=', self.from_date),
                                  ('state', 'in', ('item_in_receiving', 'item_received'))])
        for sa in shipment_advice:
            if sa.bl_entry_id and sa.bl_entry_id not in bl_list:
                bl_list.append(sa.bl_entry_id)

        return bl_list

    def _get_currency_rate(self, bl):
        currency = bl.bl_entry_lines.mapped('currency_id')
        filtered_rate_ids = currency.rate_ids.filtered(lambda x: x.name < bl.bl_date)
        currency_rec = filtered_rate_ids.filtered(lambda x: x.name == max(filtered_rate_ids.mapped('name')))
        if not (currency_rec and currency_rec.inverse_company_rate):
            return 1
        return currency_rec.inverse_company_rate

    def _get_landed_cost_data(self, bl):
        # cost_names = []
        product_list = []
        product_discounts = self._get_product_discounts(bl)
        for sa in bl.shipment_advices:
            for salc in sa.landed_cost_to_apply:
                for slc in salc.move_id.landed_costs_ids:
                    # cost_names.extend(slc.valuation_adjustment_lines.mapped('cost_line_id.name'))
                    for cl in slc.valuation_adjustment_lines:
                        product_info = {}
                        added_already = False
                        for dict in product_list:
                            if dict['lot'] == cl.move_id.lot_id.name and dict['product_code'] == cl.move_id.product_id.default_code:
                                added_already = True
                                if cl.cost_line_id.name in dict:
                                    dict[cl.cost_line_id.name] = dict[cl.cost_line_id.name] + cl.additional_landed_cost
                                else:
                                    dict[cl.cost_line_id.name] = cl.additional_landed_cost
                            if added_already: break
                        if added_already: continue
                        product_info['date'] = sa.arrival_date
                        product_info['lot'] = cl.move_id.lot_id.name
                        product_info['product_name'] = cl.move_id.product_id.name
                        product_info['product_code'] = cl.move_id.product_id.default_code
                        product_info['container'] = sa.bl_entry_container_id.container_number
                        product_info['quantity'] = cl.quantity
                        conversion = max(cl.move_id.product_id.packaging_ids.mapped('qty'))
                        product_info['conversion'] = conversion
                        product_info['qty_rcvd'] = cl.quantity / conversion
                        product_info['principal_disc'] = sum(product['principal_disc'] * product_info['qty_rcvd'] for product in product_discounts if product['product_code'] == cl.move_id.product_id.default_code)
                        product_info['contractual_disc'] = sum(product['contractual_disc'] * product_info['qty_rcvd'] for product in product_discounts if product['product_code'] == cl.move_id.product_id.default_code)
                        product_info['additional_disc'] = sum(product['additional_disc'] * product_info['qty_rcvd'] for product in product_discounts if product['product_code'] == cl.move_id.product_id.default_code)
                        product_info[cl.cost_line_id.name] = cl.additional_landed_cost
                        bl_line = bl.bl_entry_lines.filtered(lambda x: x.product_id.id == cl.move_id.product_id.id and x.container_id.container_number == sa.bl_entry_container_id.container_number)
                        product_info['ad_price'] = bl_line[0].bl_price
                        product_info['bd_price'] = bl_line[0].lpo_price
                        product_info['pp_ad'] = (cl.quantity / conversion) * bl_line[0].bl_price
                        product_list.append(product_info)
        # cost_names = list(set(cost_names))
        # return cost_names, product_list
        return product_list

    def _get_product_discounts(self, bl):
        product_discounts = []

        # Discount 1 and 2 creation
        for bill_line in bl.invoice_ids.filtered(lambda x: x.po_discount_entry_id).invoice_line_ids:
            new_str = bl.name + bill_line.product_id.name
            lines = bl.invoice_ids.po_discount_entry_id.invoice_line_ids.filtered(lambda x: x.name.endswith(new_str))
            if not lines:
                disc1 = 0
                disc2 = 0
            else:
                disc1 = max(lines.mapped('price_total')) / bill_line.product_packaging_qty
                disc2 = min(lines.mapped('price_total')) / bill_line.product_packaging_qty
            product_discounts.append({'product_code': bill_line.product_id.default_code,
                                      'product_name': bill_line.product_id.name,
                                      'quantity': bill_line.product_packaging_qty,
                                      'principal_disc': disc1,
                                      'contractual_disc': disc2})

        # Discount 3 Creation.
        compare_str = "Additional Discount : "
        disc3_bill = bl.invoice_ids.filtered(lambda x: not x.po_discount_entry_id and x.ref == ("Additional Discount : " + bl.name))
        for product in product_discounts:
            new_str = compare_str + product['product_name'] + " " + bl.name
            product['additional_disc'] = sum(disc3_bill.invoice_line_ids.filtered(lambda x: x.name.startswith(new_str)).mapped('credit')) / product['quantity']
        return product_discounts




