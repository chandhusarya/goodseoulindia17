from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
import io
import base64
import xlsxwriter
from twilio.rest import Client
import json



class StockReportForSales(models.Model):
    _name = 'stock.report.for.sales'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    to_email = fields.Char("To Email")
    company_id = fields.Many2one(comodel_name='res.company', string='Company')
    locations = fields.Many2many('stock.location', 'stock_report_sales_location', 'report_id', 'location_id',
                                 string='Locations', domain="[('usage', '=', 'internal')]")

    employees = fields.Many2many('hr.employee', 'stock_report_sales_employee', 'stock_report_id',
                                                    'employee_id', string='Employees')


    def generate_excel_report(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Stock Summary Report")

        # Set white background (default in most cases)
        column_header_format = workbook.add_format({'bg_color': '#FFFF00', 'font_color': '#000000', 'bold': True, 'border':1})
        column_header_format_no_stock = workbook.add_format({'bg_color': '#FFFFFF', 'font_color': '#FF0000', 'bold': True, 'border': 1})
        data_format = workbook.add_format({'bg_color': '#FFFFFF', 'font_color': '#000000', 'border':1})

        #  header
        y_value, x_value = 1, 0
        worksheet.write(y_value, x_value, 'Sn. No.', column_header_format)
        worksheet.write(y_value, x_value+1, 'Item Description', column_header_format)
        worksheet.write(y_value, x_value+2, 'Category', column_header_format)
        worksheet.write(y_value, x_value+3, 'Pack Size', column_header_format)
        worksheet.write(y_value, x_value+4, 'Physical Stock', column_header_format)

        #Width of columns
        worksheet.set_column(0, 0, 10)
        worksheet.set_column(1, 1, 65)
        worksheet.set_column(2, 2, 10)
        worksheet.set_column(3, 3, 10)
        worksheet.set_column(4, 4, 15)


        stock_details = self.get_stock()
        all_sales_data, others_detailed, others_summary = self.get_sales()

        print("\n\nstock_details   ===============>> ", stock_details)
        print("\n\nall_sales_data  ===============>> ", all_sales_data)
        print("\n\nothers_detailed ===============>> ", others_detailed)
        print("\n\nothers_summary  ===============>> ", others_summary)



        #make customer mapping
        customer_list = []
        for product_id in all_sales_data:
            print("product_id ===>>> ", product_id)
            for customer_id in all_sales_data[product_id]:
                if customer_id not in customer_list:
                    customer_list.append(customer_id)

        print("\n\n\n\ncustomer_list ===============>> ", customer_list)

        customer_mapping_x = {}
        maximum_customers = 0
        others_x = 4
        if customer_list:
            customers = self.env['res.partner'].browse(customer_list)
            x_value = 4
            for customer in customers:
                x_value += 1
                worksheet.write(y_value, x_value, customer.name, column_header_format)
                customer_mapping_x[customer.id] = x_value
                worksheet.set_column(x_value, x_value, len(customer.name) + 1)
                if maximum_customers < x_value:
                    maximum_customers = x_value

        if others_summary:
            others_x = maximum_customers if maximum_customers > others_x else others_x
            worksheet.write(y_value, maximum_customers+1, "Others", column_header_format)
            worksheet.set_column(maximum_customers+1, maximum_customers+1, len("Others") + 1)

        worksheet.write(y_value, maximum_customers + 2, "Closing Stock", column_header_format)
        worksheet.set_column(maximum_customers + 2, maximum_customers + 1, len("Closing Stock") + 1)

        sl_no = 0
        items_in_stock = []
        for stock in stock_details:


            x_value = 0
            sl_no += 1
            y_value += 1
            items_in_stock.append(stock.get('product_id'))

            worksheet.write(y_value, x_value, sl_no, data_format)
            worksheet.write(y_value, x_value+1, stock.get('item_description'), data_format)
            worksheet.write(y_value, x_value+2, stock.get('category'), data_format)
            worksheet.write(y_value, x_value+3, stock.get('pack_size'), data_format)
            worksheet.write(y_value, x_value+4, round(stock.get('quantity', 0), 2), data_format)

            closing_stock = stock.get('quantity', 0)

            sales_data = all_sales_data.get(stock.get('product_id'))
            non_empty_columns = []
            if sales_data:
                for customer_id in sales_data:
                    if customer_id in customer_mapping_x:
                        x_value = customer_mapping_x[customer_id]
                        qty = sales_data[customer_id].get('qty', 0)/stock.get('pack_size')
                        worksheet.write(y_value, x_value, round(qty, 2), data_format)
                        non_empty_columns.append(x_value)

                        # Calculate closing stock
                        closing_stock -= qty

            if others_summary:
                x_value = maximum_customers + 1
                if stock.get('product_id') in others_summary:
                    non_empty_columns.append(x_value)
                    qty = others_summary[stock.get('product_id')].get('qty', 0)/stock.get('pack_size')
                    worksheet.write(y_value, x_value, round(qty, 2), data_format)
                    closing_stock -= others_summary[stock.get('product_id')].get('qty', 0)/stock.get('pack_size')

            worksheet.write(y_value, maximum_customers + 2, round(closing_stock, 2), data_format)


            if maximum_customers > 4:
                to_range = maximum_customers+2 if others_summary else maximum_customers+1
                for x in range(5, to_range):
                    if x not in non_empty_columns:
                        worksheet.write(y_value, x, '', data_format)

        #Add non stock items in sales order
        non_stock_products = []
        non_stock_sales_data = {}
        non_stock_others_summary = {}
        for product_id in all_sales_data:
            if product_id not in items_in_stock:
                non_stock_sales_data[product_id] = all_sales_data[product_id]
                non_stock_products.append(product_id)


        for product_id in others_summary:
            if product_id not in items_in_stock:
                if product_id not in non_stock_products:
                    non_stock_products.append(product_id)
                non_stock_others_summary[product_id] = others_summary[product_id]


        if non_stock_products:
            y_value = y_value + 2
            worksheet.merge_range(y_value, 0, y_value, maximum_customers + 2, "Order Received for No Stock Items", column_header_format_no_stock)


            for product_id in non_stock_products:
                x_value = 0
                y_value += 1
                closing_stock = 0
                sl_no += 1
                product = self.env['product.product'].browse(product_id)

                carton = False
                for packaging in product.packaging_ids:
                    if not carton:
                        carton = packaging
                    elif packaging.qty > carton.qty:
                        carton = packaging

                worksheet.write(y_value, x_value, sl_no, data_format)
                worksheet.write(y_value, x_value + 1, product.name, data_format)
                worksheet.write(y_value, x_value + 2, product.categ_id.name if product.categ_id else 'N/A', data_format)
                worksheet.write(y_value, x_value + 3, carton.qty if carton else 1, data_format)
                worksheet.write(y_value, x_value + 4, "", data_format)

                #Non stock items will not have physical stock
                non_empty_columns = []
                if product_id in non_stock_sales_data:
                    for partner_id in non_stock_sales_data[product_id]:
                        if partner_id in customer_mapping_x:
                            x_value = customer_mapping_x[partner_id]
                            non_empty_columns.append(x_value)
                            qty = non_stock_sales_data[product_id][partner_id].get('qty', 0)/carton.qty
                            worksheet.write(y_value, x_value, round(qty, 2), data_format)
                            closing_stock -= qty

                # Non stock other items will not have physical stock
                qty = ""
                if product_id in non_stock_others_summary:
                    qty = non_stock_others_summary[product_id].get('qty', 0)/carton.qty if carton else 1
                    closing_stock -= qty
                    qty = round(qty, 2)

                worksheet.write(y_value, maximum_customers + 1, qty, data_format)
                worksheet.write(y_value, maximum_customers + 2, round(closing_stock, 2), data_format)

                if maximum_customers > 4:
                    to_range = maximum_customers + 1
                    for x in range(5, to_range):
                        if x not in non_empty_columns:
                            worksheet.write(y_value, x, '', data_format)

        if others_detailed:
            y_value = 0
            sl_no = 0
            worksheet_others = workbook.add_worksheet("Others Detailed Report")

            y_value, x_value = 1, 0
            worksheet_others.write(y_value, x_value, 'Sn. No.', column_header_format)
            worksheet_others.write(y_value, x_value + 1, 'Item Description', column_header_format)
            worksheet_others.write(y_value, x_value + 2, 'Category', column_header_format)
            worksheet_others.write(y_value, x_value + 3, 'Pack Size', column_header_format)

            # Width of columns
            worksheet_others.set_column(0, 0, 10)
            worksheet_others.set_column(1, 1, 65)
            worksheet_others.set_column(2, 2, 10)
            worksheet_others.set_column(3, 3, 10)

            # make customer mapping
            customer_list = []
            for product_id in others_detailed:
                for customer_id in others_detailed[product_id]:
                    if customer_id not in customer_list:
                        customer_list.append(customer_id)

            customer_mapping_x = {}
            maximum_customers = 0
            if customer_list:
                customers = self.env['res.partner'].browse(customer_list)
                x_value = 3
                for customer in customers:
                    x_value += 1
                    worksheet_others.write(y_value, x_value, customer.name, column_header_format)
                    customer_mapping_x[customer.id] = x_value
                    worksheet_others.set_column(x_value, x_value, len(customer.name) + 1)
                    if maximum_customers < x_value:
                        maximum_customers = x_value







            for product_id in others_detailed:
                x_value = 0
                y_value += 1
                closing_stock = 0
                sl_no += 1
                product = self.env['product.product'].browse(product_id)

                carton = False
                for packaging in product.packaging_ids:
                    if not carton:
                        carton = packaging
                    elif packaging.qty > carton.qty:
                        carton = packaging

                worksheet_others.write(y_value, x_value, sl_no, data_format)
                worksheet_others.write(y_value, x_value + 1, product.name, data_format)
                worksheet_others.write(y_value, x_value + 2, product.categ_id.name if product.categ_id else 'N/A', data_format)
                worksheet_others.write(y_value, x_value + 3, carton.qty if carton else 1, data_format)

                non_empty_columns = []
                for partner_id in others_detailed[product_id]:
                    if partner_id in customer_mapping_x:
                        x_value = customer_mapping_x[partner_id]
                        non_empty_columns.append(x_value)
                        qty = others_detailed[product_id][partner_id].get('qty', 0)/carton.qty
                        worksheet_others.write(y_value, x_value, round(qty, 2), data_format)
                        closing_stock -= qty



                if maximum_customers > 4:
                    to_range = maximum_customers + 1
                    for x in range(4, to_range):
                        if x not in non_empty_columns:
                            worksheet_others.write(y_value, x, '', data_format)

        # Adding detailed stock report
        self.env['report.sry_forecast_analysis.stock_onhand_report'].generate_xlsx_report(workbook, {'company_ids': self.company_id.ids}, [])


        workbook.close()
        output.seek(0)

        return output.read()


    def get_sales(self):
        product_wise_sales_data = {}
        others_summary = {}
        others_detailed = {}
        sales_orders = self.env['sale.order'].sudo().search([('state', 'in', ['sale', 'done']), ('company_id', '=', self.company_id.id)])
        for order in sales_orders:
            is_stock_delivered = False
            for picking in order.picking_ids:
                if picking.state in ['done', 'cancel']:
                    is_stock_delivered = True
            if not is_stock_delivered:
                for line in order.order_line:
                    product = line.product_id

                    qty = line.product_uom_qty

                    # Check if customer is distributer
                    if order.partner_id.trade_channel.name == 'DISTRIBUTION':

                        if product.id not in product_wise_sales_data:
                            product_wise_sales_data[product.id] = {order.partner_id.id : {'qty' : qty}}
                        else:
                            if order.partner_id.id not in product_wise_sales_data[product.id]:
                                product_wise_sales_data[product.id][order.partner_id.id] = {'qty' : qty}
                            else:
                                product_wise_sales_data[product.id][order.partner_id.id]['qty'] += qty
                    else:
                        if product.id not in others_detailed:
                            others_detailed[product.id] = {order.partner_id.id : {'qty' : qty}}
                        else:
                            if order.partner_id.id not in others_detailed[product.id]:
                                others_detailed[product.id][order.partner_id.id] = {'qty' : qty}
                            else:
                                others_detailed[product.id][order.partner_id.id]['qty'] += qty


                        if product.id not in others_summary:
                            others_summary[product.id] = {'qty' : qty}
                        else:
                            others_summary[product.id]['qty'] += qty

        return product_wise_sales_data, others_detailed, others_summary



    def get_stock(self):

        location = self.locations.ids

        quants = self.env['stock.quant'].sudo().search([
            ('location_id', 'in', location)
        ])

        stock_data = []
        stock_data_dict = {}
        for quant in quants:


            if quant.product_id.type != 'product':
                continue

            print("\n\n\n\nquant.product_id.id ===>>", quant.product_id.id)

            carton = False
            for packaging in quant.product_id.packaging_ids:
               if not carton:
                    carton = packaging
               elif packaging.qty > carton.qty:
                    carton = packaging

            if quant.product_id.id in stock_data_dict:
                stock_data_dict[quant.product_id.id]['quantity'] += quant.quantity/carton.qty if carton else quant.quantity
            else:
                stock_data_dict[quant.product_id.id] = {
                    'product_id': quant.product_id.id,
                    'item_description': quant.product_id.name,
                    'category': quant.product_id.categ_id.name if quant.product_id.categ_id else 'N/A',
                    'pack_size': carton.qty if carton else 1,
                    'quantity': quant.quantity/carton.qty if carton else quant.quantity,
                }

        for product_id in stock_data_dict:
            stock_data.append(stock_data_dict[product_id])

        print("\n\n\nget_stock ===============>> ", stock_data)

        return stock_data



    def button_generate_stock_report(self):
        file_content = self.generate_excel_report()
        file_name = f'Stock_Report_{fields.Datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'res_model': self._name,
            'res_id': self.id,
            'type': 'binary',
            'datas': base64.b64encode(file_content),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        # Post to chatter
        self.message_post(
            body=f"Stock report generated and attached.",
            attachment_ids=[attachment.id]
        )


    def button_email_stock_report(self):
        file_content = self.generate_excel_report()
        file_name = f'Stock_Report_{fields.Datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'res_model': self._name,
            'res_id': self.id,
            'type': 'binary',
            'datas': base64.b64encode(file_content),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        # Prepare email content
        formatted_date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mail_subj = f"India Stock Balance report {formatted_date_time}"
        mail_content = f"Hello,<br>Attached Stock balance Report as on {formatted_date_time}"
        to_email = ""
        for emp in self.employees:
            if emp.work_email:
                to_email += emp.work_email + ", "

        main_content = {
            'subject': mail_subj,
            'body_html': mail_content,
            'email_to': to_email,
            'attachment_ids': attachment.ids,
        }
        self.env['mail.mail'].sudo().create(main_content).send()

        for emp in self.employees:
            if emp.whatsapp_number:
                to_number = "whatsapp:%s" % emp.whatsapp_number
                fir_param = emp.name + ", Please click below button to download the stock report"
                sec_param = f"/content/{attachment.id}/{attachment.name}?download=true"
                self.send_by_whatsapp(fir_param, sec_param, to_number)


    def send_by_whatsapp(self, fir_param, sec_param, to_number):
        account_sid = self.env['ir.config_parameter'].sudo().get_param('twilio.account_sid', False)
        auth_token = self.env['ir.config_parameter'].sudo().get_param('twilio.auth_token', False)
        from_number = self.env['ir.config_parameter'].sudo().get_param('twilio.from', False)
        from_number = "whatsapp:%s" % from_number
        if account_sid and auth_token and from_number and to_number:
            content_variables = json.dumps({"1": fir_param,
                                            "2": sec_param})
            client = Client(account_sid, auth_token)
            message = client.messages.create(
                from_=from_number,
                content_sid='HXbecfa3982f02c410ede41a204763e958',
                content_variables=content_variables,
                to=to_number)

        else:
            raise UserError(_("Missing configuration, please contact the administrator %s."%to_number))







    def scheduler_stock_balance_report(self):

        all_report = self.search([])
        for report in all_report:
            report.button_email_stock_report()



