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

    def get_sales_data(self, outlet):
        product_wise_data = {}
        pos_picking_type_id = outlet.picking_type_id

        source_location_id = pos_picking_type_id.default_location_src_id and pos_picking_type_id.default_location_src_id.id
        sales_order = self.env['sale.order'].search([
            ('date_order', '>=', self.from_date),
            ('date_order', '<=', self.to_date),
            ('picking_type_id', '=', pos_picking_type_id.id),
            ('state', '=', 'sale')])

        packaging_category = self.env['product.category'].search([('name', 'ilike', 'Packaging')])

        for so in sales_order:
            for line in so.order_line:
                print("Product : ", line.product_id.name)
                include_prd_in_sales = False
                cost = 0
                packaging_cost = 0
                for mv in line.move_ids:
                    if mv.state == 'done':
                        include_prd_in_sales = True
                    for val in mv.stock_valuation_layer_ids:
                        if mv.product_id.categ_id.id in packaging_category.ids:
                            packaging_cost += val.value
                        else:
                            cost += val.value

                cost = cost * -1
                packaging_cost = packaging_cost * -1

                if include_prd_in_sales:
                    if line.product_id.id not in product_wise_data:
                        base = ''
                        packaging = ''
                        mrp_bom = self.env['mrp.bom'].search([('product_id', '=', line.product_id.id)], limit=1)
                        for bom_line in mrp_bom.bom_line_ids:
                            bom_product = bom_line.product_id.name
                            bom_product_qty = bom_line.product_qty/mrp_bom.product_qty
                            bom_primary_packaging_name = bom_line.primary_packaging_id.name
                            bom_text = "%s%s %s" % (str(bom_product_qty), bom_primary_packaging_name, bom_product)

                            if bom_line.product_id.categ_id.id in packaging_category.ids:
                                if packaging:
                                    packaging = "%s, %s" % (packaging, bom_text)
                                else:
                                    packaging = bom_text
                            else:
                                if base:
                                    base = "%s, %s" % (base, bom_text)
                                else:
                                    base = bom_text

                        product_wise_data[line.product_id.id] = {
                            'product_id': line.product_id.id,
                            'product_name': line.product_id.name,
                            'default_code': line.product_id.default_code,
                            'sales_amt': line.price_subtotal,
                            'sales_qty': line.product_uom_qty,
                            'cost': cost,
                            'packaging_cost': packaging_cost,
                            'base': base,
                            'packaging': packaging
                        }
                    else:
                        product_wise_data[line.product_id.id]['sales_amt'] += line.price_subtotal
                        product_wise_data[line.product_id.id]['sales_qty'] += line.product_uom_qty
                        product_wise_data[line.product_id.id]['cost'] += cost
                        product_wise_data[line.product_id.id]['packaging_cost'] += packaging_cost

        result = []
        for product_id in product_wise_data:
            data = product_wise_data[product_id]
            if data['sales_amt'] > 0 and (data['cost'] > 0 or data['packaging_cost'] > 0):
                fd_cost_perc = 0
                packaging_cost_perc = 0
                sales_amt = data['sales_amt']
                cost = data['cost']
                packaging_cost = data['packaging_cost']
                if cost > 0 and sales_amt > 0:
                    fd_cost_perc = (cost/sales_amt) * 100
                if packaging_cost > 0 and sales_amt > 0:
                    packaging_cost_perc = (packaging_cost/sales_amt) * 100

                data['fd_cost_perc'] = fd_cost_perc
                data['packaging_cost_perc'] = packaging_cost_perc
            result.append(data)
        return result

    def get_material_data(self, outlet):

        product_wise_data = {}

        pos_picking_type_id = outlet.picking_type_id

        source_location_id = pos_picking_type_id.default_location_src_id and pos_picking_type_id.default_location_src_id.id


        #Find valuationlayer related our location
        #Get Opening Stock
        opening_valuation_layer = self.env['stock.valuation.layer']._read_group([
            "|", ('stock_move_id.location_id', '=', source_location_id),
            ('stock_move_id.location_dest_id', '=', source_location_id),
            ('create_date', '<', self.from_date)],
            ['product_id'], ['quantity:sum', 'value:sum'])



        #Adding Opening stock
        for open_val in opening_valuation_layer:
            product = open_val[0]
            quantity = open_val[1]
            value = open_val[2]

            primary_packaging = ''
            for pack in product.packaging_ids:
                if pack.primary_unit:
                    primary_packaging = pack.name

            product_wise_data[product.id] = {
                'product_name': product.name,
                'product_uom': primary_packaging,
                'beginning_inv': quantity,
                'beginning_inv_value': value
            }

        # Get Closing Stock
        closing_valuation_layer = self.env['stock.valuation.layer']._read_group([
            "|", ('stock_move_id.location_id', '=', source_location_id),
            ('stock_move_id.location_dest_id', '=', source_location_id),
            ('create_date', '<=', self.to_date)],
            ['product_id'], ['quantity:sum', 'value:sum'])

        #Adding Closing Stock
        for closing_val in closing_valuation_layer:
            product = closing_val[0]
            quantity = closing_val[1]
            value = closing_val[2]
            if product.id not in product_wise_data:

                primary_packaging = ''
                for pack in product.packaging_ids:
                    if pack.primary_unit:
                        primary_packaging = pack.name

                product_wise_data[product.id] = {
                    'product_name': product.name,
                    'product_uom': primary_packaging,
                    'ending_inv': quantity,
                    'ending_inv_value': value
                }
            else:
                product_wise_data[product.id]['ending_inv'] = quantity
                product_wise_data[product.id]['ending_inv_value'] = value

        #HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH
        #HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH
        #HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH

        print("product_wise_data 111111111111111111 ==>> ", product_wise_data)

        # Get Purchase Stock
        purchase_valuation_layer = self.env['stock.valuation.layer']._read_group([
            ('stock_move_id.location_dest_id', '=', source_location_id),
            ('create_date', '>=', self.from_date),
            ('create_date', '<=', self.to_date)],
            ['product_id'], ['quantity:sum', 'value:sum'])

        # Adding Purchase Stock
        for purchase_val in purchase_valuation_layer:
            product = purchase_val[0]
            quantity = purchase_val[1]
            value = purchase_val[2]
            if product.id not in product_wise_data:

                primary_packaging = ''
                for pack in product.packaging_ids:
                    if pack.primary_unit:
                        primary_packaging = pack.name

                product_wise_data[product.id] = {
                    'product_name': product.name,
                    'product_uom': primary_packaging,
                    'purchase': quantity,
                    'purchase_value': value
                }
            else:
                product_wise_data[product.id]['purchase'] = quantity
                product_wise_data[product.id]['purchase_value'] = value


        print("product_wise_data 2222222 ==>> ", product_wise_data)

        # Get Usage Stock
        usage_valuation_layer = self.env['stock.valuation.layer']._read_group([
            ('stock_move_id.location_id', '=', source_location_id),
            ('create_date', '>=', self.from_date),
            ('create_date', '<=', self.to_date)],
            ['product_id'], ['quantity:sum', 'value:sum'])

        # Adding Usage Stock
        for usage_val in usage_valuation_layer:
            product = usage_val[0]
            quantity = usage_val[1]
            value = usage_val[2]
            if product.id not in product_wise_data:

                primary_packaging = ''
                for pack in product.packaging_ids:
                    if pack.primary_unit:
                        primary_packaging = pack.name

                product_wise_data[product.id] = {
                    'product_name': product.name,
                    'product_uom': primary_packaging,
                    'usage': quantity,
                    'usage_value': value
                }
            else:
                product_wise_data[product.id]['usage'] = quantity
                product_wise_data[product.id]['usage_value'] = value

        print("product_wise_data 3333333333 ==>> ", product_wise_data)



        result = []
        for product_id in product_wise_data:
            data = product_wise_data[product_id]
            result.append(data)

        return result





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
            {'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 6, 'font_color': '#666666', 'text_wrap': True})
        level_1_style = workbook.add_format(
            {'font_name': 'Arial', 'bold': False, 'font_size': 13, 'bottom': 6, 'font_color': '#666666',
             'text_wrap': True})


        from_date, to_date = self.from_date, self.to_date
        x_value, y_value = 0,0
        sheet.set_column(0, 0, 35)
        sheet.set_column(1, 1, 45)
        sheet.set_column(2, 2, 45)
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
            sheet.write(y_value, x_value, "Sales vs COGS", level_0_style)
            y_value += 1
            sheet.write(y_value, x_value, 'Menu', level_0_style)
            sheet.write(y_value, x_value + 1, 'Base', level_0_style)
            sheet.write(y_value, x_value + 2, 'Packaging', level_0_style)
            sheet.write(y_value, x_value + 3, 'Food Cost', level_0_style)
            sheet.write(y_value, x_value + 4, 'Packaging Cost', level_0_style)
            sheet.write(y_value, x_value + 5, 'Sales Qty', level_0_style)
            sheet.write(y_value, x_value + 6, 'Sales Amount', level_0_style)
            sheet.write(y_value, x_value + 7, 'Food Cost(%)', level_0_style)
            sheet.write(y_value, x_value + 8, 'Packaging Cost(%)', level_0_style)
            y_value += 1
            product_wise_data = self.get_sales_data(outlet)
            for value in product_wise_data:
                sheet.write(y_value, x_value, value['product_name'], level_1_style)
                sheet.write(y_value, x_value + 1, 'base' in value and value['base'] or '', level_1_style)
                sheet.write(y_value, x_value + 2, 'packaging' in value and value['packaging'] or '', level_1_style)
                sheet.write(y_value, x_value + 3, 'cost' in value and value['cost'] or 0, level_1_style)
                sheet.write(y_value, x_value + 4, 'packaging_cost' in value and value['packaging_cost'] or 0, level_1_style)
                sheet.write(y_value, x_value + 5, 'sales_qty' in value and value['sales_qty'] or 0, level_1_style)
                sheet.write(y_value, x_value + 6, 'sales_amt' in value and value['sales_amt'] or 0, level_1_style)
                sheet.write(y_value, x_value + 7, 'fd_cost_perc' in value and value['fd_cost_perc'] or 0, level_1_style)
                sheet.write(y_value, x_value + 8, 'packaging_cost_perc' in value and value['packaging_cost_perc'] or 0, level_1_style)
                y_value += 1

            y_value += 1
            sheet.write(y_value, x_value, "Material Cost", level_0_style)
            y_value += 1
            sheet.write(y_value, x_value, 'Item', level_0_style)
            sheet.write(y_value, x_value + 1, 'Uom', level_0_style)
            sheet.write(y_value, x_value + 2, 'Beginning Stock', level_0_style)
            sheet.write(y_value, x_value + 3, 'Beginning Stock Value', level_0_style)
            sheet.write(y_value, x_value + 4, 'Purchase', level_0_style)
            sheet.write(y_value, x_value + 5, 'Purchase Value', level_0_style)
            sheet.write(y_value, x_value + 6, 'Usage', level_0_style)
            sheet.write(y_value, x_value + 7, 'Usage Value', level_0_style)
            sheet.write(y_value, x_value + 8, 'Ending Stock', level_0_style)
            sheet.write(y_value, x_value + 9, 'Ending Stock Value', level_0_style)
            y_value += 1
            product_wise_data = self.get_material_data(outlet)
            for value in product_wise_data:

                print("\n\nvalue =====>> ", value)

                sheet.write(y_value, x_value, value['product_name'])
                sheet.write(y_value, x_value + 1, 'product_uom' in value and value['product_uom'] or '')
                sheet.write(y_value, x_value + 2, 'beginning_inv' in value and value['beginning_inv'] or 0)
                sheet.write(y_value, x_value + 3, 'beginning_inv_value' in value and value['beginning_inv_value'] or 0)
                sheet.write(y_value, x_value + 4, 'purchase' in value and value['purchase'] or 0)
                sheet.write(y_value, x_value + 5, 'purchase_value' in value and value['purchase_value'] or 0)
                sheet.write(y_value, x_value + 6, 'usage' in value and value['usage'] or 0)
                sheet.write(y_value, x_value + 7, 'usage_value' in value and value['usage_value'] or 0)
                sheet.write(y_value, x_value + 8, 'ending_inv' in value and value['ending_inv'] or 0)
                sheet.write(y_value, x_value + 9, 'ending_inv_value' in value and value['ending_inv_value'] or 0)
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

