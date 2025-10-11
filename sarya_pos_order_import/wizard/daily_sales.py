from odoo import fields, models, api, _
import tempfile
import binascii
import xlrd
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)
try:
    import xlwt
except ImportError:
    _logger.debug('Cannot `import xlwt`.')
try:
    import cStringIO
except ImportError:
    _logger.debug('Cannot `import cStringIO`.')
try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')



class DailySales(models.TransientModel):
    _name = 'daily.sales.import'
    _description = 'Daily Sales import wizard'

    customer_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer', required=True, domain=[('customer_rank', '>', 0)])
    date = fields.Date(
        string='Sales Date',
        required=True)
    new_field = fields.Binary(string="File")
    file_name = fields.Char("Image Filename")
    is_import_file = fields.Boolean('IS Import File', default=False)

    @api.onchange('new_field')
    def _onchange_is_import_file(self):
        for rec in self:
            if rec.new_field:
                rec.is_import_file = True
            else:
                rec.is_import_file = False

    def make_sale_line(self, values, sale_id):
        product_obj = self.env['product.product']
        sale_line_obj = self.env['sale.order.line']
        for value in values:
            product_search = product_obj.search([('sale_ok', '=', True), ('ps_origin', '=', value['item_code'])])
            if product_search:
                product_id = product_search
            elif value['item_code']:

                msg ="item code not found in odoo %s " % (value['item_code'])
                raise UserError(_(msg))
            else:
                continue

            product_uom = product_search.uom_id
            net_sale_amt = float(value['net_sale_amt'])
            qty = float(value['qty'])
            if qty > 0:
                unit_price = net_sale_amt/qty
            else:
                unit_price = 0

            if product_id.taxes_id:
                for tax in product_id.taxes_id:
                    tax_percentage = 0
                    for child in tax.children_tax_ids:
                        tax_percentage += child.amount

                    if tax_percentage:
                        unit_price = unit_price / (1 + tax_percentage / 100)



            primary_packaging_id = self.env['product.packaging'].search(
                [('product_id', '=', product_id.id), ('primary_unit', '=', True)])
            dd = {
                'order_id': sale_id.id,
                'product_id': product_id.id,
                'name': value['item_name'],
                'product_packaging_id': primary_packaging_id and primary_packaging_id.id,
                'product_uom_qty': qty,
                'product_packaging_qty': qty,
                'price_unit': unit_price,
                'pkg_unit_price': unit_price,
            }
            print("DD", dd)
            so_order_lines = sale_line_obj.create({
                'order_id': sale_id.id,
                'product_id': product_id.id,
                'name': value['item_name'],
                'product_packaging_id': primary_packaging_id and primary_packaging_id.id,
                'product_uom_qty': qty,
                'product_packaging_qty': qty,
                'price_unit': unit_price,
                'pkg_unit_price': unit_price,
            })

        return True

    def make_sale(self, values):
        partner_invoice_id = self.customer_id and self.customer_id.parent_customer_id or self.customer_id
        sale_id = self.env['sale.order'].create({'partner_id':self.customer_id.id,
                                                 'partner_invoice_id': partner_invoice_id.id,
                                                'date_order': self.date,
                                                'pos_import_sales_date': self.date,
                                                'customer_lpo_date': self.date,
                                                'commitment_date': self.date,
                                                'delivery_deadline_date': self.date,
                                                'picking_type_id': self.customer_id.picking_type_id.id,
                                                'journal_id': self.customer_id.journal_id and self.customer_id.journal_id.id,
                                                })
        self.make_sale_line(values, sale_id)
        return sale_id


    def import_orders(self):
        """Load Product data from the XLS file."""
        if self.env.company and self.env.company.company_type != 'retail':
            raise ValidationError(_('Please switch to company Good Seoul before import.'))
        if not self.is_import_file:
            raise ValidationError(_('Please upload import file'))
        if self.customer_id and not self.customer_id.picking_type_id:
            raise ValidationError(_('Please mention picking type in customer.'))
        not_imported = []
        if self.new_field:
            if self.file_name.endswith(('.xlsx', '.xlsm', '.xlsb', '.xltx', '.xltm', '.xls', '.xlt', '.xls', '.xlam',
                                       '.xla', '.xlw', '.xlr')):
                fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                fp.write(binascii.a2b_base64(self.new_field))
                fp.seek(0)
                values = []
                sale_ids = []
                workbook = xlrd.open_workbook(fp.name)
                sheet = workbook.sheet_by_index(0)
                product_obj = self.env['product.product']
                date_string = False
                is_item_line = False
                for row_no in range(sheet.nrows):
                    val = {}
                    tax_line = ''
                    if row_no <= 0:
                        fields = map(lambda row: row.value.encode('utf-8'), sheet.row(row_no))
                    else:
                        line = list(
                            map(lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(
                                row.value),
                                sheet.row(row_no)))
                        if 'Item Code' in line or 'Item Name' in line:
                            row_no += 2
                            is_item_line = True
                            continue
                        if is_item_line:
                            values.append({
                                'item_code': line[0],
                                'item_name': line[1],
                                'qty': line[2],
                                'sale_amt': line[3],
                                'net_sale_amt': line[4],
                                'brand': line[5],
                                'category': line[6],
                                'sub_category': line[7],
                                'mc_code': line[8],
                                'sku_type': line[9],
                                'stock_value': line[10],
                                'tax': line[11],
                                'floor': line[12],
                            })

                res = self.make_sale(values)


                '''Attach the import file to system for future reference'''
                # binary_data_base64 = base64.b64encode(self.new_field).decode('utf-8')
                attachment_data = {
                    'name': self.file_name,
                    'datas': self.new_field,
                    'type': 'binary',
                    'res_model': 'sale.order',
                    'res_id': res.id,
                }
                attachment = self.env['ir.attachment'].create(attachment_data)
                res.write({
                    'lpo_attach_id': [(6, 0, [attachment.id])],
                })

                '''Confirm the order and delivery order'''
                #res.date_order = self.date
                result = res.action_confirm()
                # print('result', result)
                # for picking in res.picking_ids:
                #     picking.action_assign()
                #     picking.button_validate()

                if res:
                    return {
                        'name': 'Sale Order',
                        'type': 'ir.actions.act_window',
                        'res_model': 'sale.order',
                        'view_mode': 'form',
                        'res_id': res.id,
                    }

        else:
            raise UserError(_("Please Upload the Excel file to Continue..!"))
