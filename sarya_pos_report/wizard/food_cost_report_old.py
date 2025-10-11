from odoo import fields, models, api
import io
import json
import xlsxwriter
from odoo.exceptions import ValidationError, UserError



class FoodCostReport(models.TransientModel):
    _name = 'food.cost.report'
    _description = 'Food Cost Report'

    from_date = fields.Date(
        string='From Date', 
        required=True)
    to_date = fields.Date(
        string='To Date', 
        required=True)
    outlet_ids = fields.Many2many(
        comodel_name='pos.config',
        string='Outlet')

    # Excel Report Generation
    excel_file_name = fields.Char('Excel File Name')
    excel_file = fields.Binary("Excel File")

    def get_outlet_data(self, outlet):
        pos_picking_type_id = outlet.picking_type_id
        move_obj = self.env['stock.move']
        quant_obj = self.env['stock.quant']
        valuation_obj = self.env['stock.valuation.layer']
        partner_ids = [outlet.partner_id.id for outlet in self.outlet_ids]
        if len(partner_ids) == 0:
            raise UserError("Please link customer under POS outlet")
        source_location_id = pos_picking_type_id.default_location_src_id and pos_picking_type_id.default_location_src_id.id
        order_lines = self.env['sale.order.line']._read_group([
            ('order_id.date_order', '>=', self.from_date),
            ('order_id.date_order', '<=', self.to_date),
            ('order_id.partner_id', 'in', partner_ids)],
            ['product_id'], ['product_packaging_qty:sum', 'price_subtotal:sum', 'purchase_price:sum'])
        ordered_product_list = [{'product_id': product_id.id, 'product_name': product_id.name, 'qty': qty, 'sale': price_subtotal, 'cost': total_cost} for product_id, qty, price_subtotal, total_cost in order_lines]
        pos_product_list = []
        for prod in self.env['product.product'].search([('available_in_pos', '=', True)]):
            stock_value = []
            prod_dict = {'product_id': prod.id, 'product_name': prod.name}
            prod_dict['beg_inv'], prod_dict['in_inv'], prod_dict['clo_inv'], prod_dict['in_inv_bal'] = 0, 0, 0, 0
            opening = prod.with_context(location=source_location_id)._compute_quantities_dict(None, None, None, None, self.to_date)
            # Get the stock in transactions of
            opening_stocks_in = move_obj.search([
                ('product_id', '=', prod.id),
                ('location_dest_id', '=', source_location_id),
                ('date', '<', self.from_date),
            ])
            opening_stocks_out = move_obj.search([
                ('product_id', '=', prod.id),
                ('location_id', '=', source_location_id),
                ('date', '<', self.from_date),
            ])
            # closing_stocks = quant_obj.search([
            #     ('product_id', '=', prod.id),
            #     ('location_id', '=', source_location_id),
            #     ('date', '<', self.to_date),
            # ])
            out_move_ids = move_obj.search([
                ('product_id', '=', prod.id),
                ('location_id', '=', source_location_id),
                ('date', '>=', self.from_date),
                ('date', '<=', self.to_date),
            ])
            in_move_ids = move_obj.search([
                ('product_id', '=', prod.id),
                ('location_dest_id', '=', source_location_id),
                ('date', '>=', self.from_date),
                ('date', '<=', self.to_date),
            ])
            # if len(in_move_ids) > 0:
            #     in_stocks = valuation_obj.search([
            #         ('stock_move_id', 'in', in_move_ids)
            #     ])
            #     prod_dict['in_inv'] = sum(in_stocks.mapped('value'))
            if len(opening_stocks_in+opening_stocks_out) > 0:
                # opening_stocks = valuation_obj.search([
                #     ('stock_move_id', 'in', opening_stocks_in+opening_stocks_out)
                # ])
                beg_in = sum([i.quantity * i.lot_id.final_cost for i in opening_stocks_in])
                beg_out = -sum([i.quantity * i.lot_id.final_cost for i in opening_stocks_out])
                prod_dict['beg_inv'] = beg_in + beg_out
            if len(in_move_ids+out_move_ids) > 0:
                # in_stocks = valuation_obj.search([
                #     ('stock_move_id', 'in', in_move_ids + out_move_ids)
                # ])
                stk_in = sum([i.quantity * i.lot_id.final_cost for i in in_move_ids])
                stk_out = -sum([i.quantity * i.lot_id.final_cost for i in out_move_ids])
                prod_dict['in_inv_bal'] = stk_in + stk_out
            prod_dict['clo_inv'] = prod_dict['beg_inv'] + prod_dict['in_inv_bal']
            print("prod_dict  >>>>>>>  ", prod_dict)
            # print('movements', movements, movements[0].product_id.name, movements[0].in_date, 'loc:', movements[0].location_id.name, 'qty:', movements[0].quantity)
            pos_product_list.append(prod_dict)
        for pos_product in pos_product_list:
            for ordered_product in ordered_product_list:
                if pos_product['product_id'] == ordered_product['product_id']:
                    # print('pos_product', pos_product)
                    # print('ordered_product', ordered_product)
                    pos_product.update(ordered_product)
                    pos_product['fd_cost'] = round((pos_product['beg_inv'] + pos_product['in_inv'] - pos_product['clo_inv'])/pos_product['sale'], 2)
                    # print('pos_product(After)', pos_product)
        # print('pos_product_list:', pos_product_list)
        return pos_product_list



    def generate_report(self):
        """ Generate an Excel report with Outlet wise food cost."""
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Food Cost')
        # Define cell formats
        date_default_col1_style = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2, 'num_format': 'yyyy-mm-dd'})
        date_default_style = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'num_format': 'yyyy-mm-dd'})
        default_col1_style = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
        default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666'})
        title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
        level_0_style = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 6, 'font_color': '#666666', 'text_wrap': True, })
        level_1_style = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 1, 'font_color': '#666666'})
        level_2_col1_style = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1})
        level_2_col1_total_style = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666'})
        level_2_style = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666'})
        level_3_col1_style = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
        level_3_col1_total_style = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1})
        level_3_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666'})

        from_date, to_date = self.from_date, self.to_date
        x_value, y_value = 0,0
        sheet.set_column(0, 0, 35)
        sheet.set_column(1, 1, 15)
        sheet.set_column(2, 2, 15)
        sheet.set_column(3, 3, 15)
        sheet.set_column(4, 4, 15)
        sheet.set_column(5, 5, 15)
        sheet.set_column(6, 6, 15)
        sheet.set_column(7, 7, 15)
        sheet.set_column(8, 8, 15)
        sheet.set_column(9, 9, 15)
        sheet.set_column(10, 10, 15)
        for outlet in self.outlet_ids:
            y_value += 3
            sheet.write(y_value, x_value, "OUTLET : " + str(outlet.name), level_0_style)
            y_value += 1
            sheet.write(y_value, x_value, 'Item', level_0_style)
            sheet.write(y_value, x_value + 1, 'Begining Inventory', level_0_style)
            sheet.write(y_value, x_value + 2, 'Transfer', level_0_style)
            sheet.write(y_value, x_value + 3, 'Ending Inventory', level_0_style)
            sheet.write(y_value, x_value + 4, 'Sales', level_0_style)
            sheet.write(y_value, x_value + 5, 'Cost', level_0_style)
            sheet.write(y_value, x_value + 6, 'Food Cost(%)', level_0_style)
            sheet.write(y_value, x_value + 7, 'Gross Profit', level_0_style)
            # sheet.write(y_value, x_value + 8, 'Deviation(%)', level_0_style)
            y_value += 1
            product_wise_data = self.get_outlet_data(outlet)
            for value in product_wise_data:
                cost, margin = 0, 0
                if 'sale' in value and 'cost' in value:
                    margin = value['sale'] - value['cost']
                sheet.write(y_value, x_value, value['product_name'])
                sheet.write(y_value, x_value + 1, 'beg_inv' in value and value['beg_inv'] or 0)
                sheet.write(y_value, x_value + 2, 'in_inv_bal' in value and value['in_inv_bal'] or 0)
                sheet.write(y_value, x_value + 3, 'clo_inv' in value and value['clo_inv'] or 0)
                sheet.write(y_value, x_value + 4, 'sale' in value and value['sale'] or 0)
                sheet.write(y_value, x_value + 5, 'cost' in value and value['cost'] or 0)
                sheet.write(y_value, x_value + 6, 'fd_cost' in value and value['fd_cost'] or 0)
                sheet.write(y_value, x_value + 7, margin)
                # sheet.write(y_value, x_value + 8, 0)
                y_value += 1

        workbook.close()
        output.seek(0)
        import base64
        generated_file = base64.b64encode(output.read())
        output.close()

        self.excel_file = generated_file
        self.excel_file_name = "Food Cost Report.xlsx"
        return {
            'name': 'FEC',
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=food.cost.report&id={}&field=excel_file&filename_field=excel_file_name&download=true'.format(
                self.id
            ),
            'target': 'self',
        }

