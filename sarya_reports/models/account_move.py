from odoo import fields, models, api
from num2words import num2words

class AccountMove(models.Model):
    _inherit = 'account.move'

    def get_tax_group(self, group=False):
        if group:
            tax_totals = self.tax_totals
            for taxes in tax_totals['groups_by_subtotal']['Untaxed Amount']:
                if taxes['tax_group_name'] == group:
                    return taxes['tax_group_amount']
        else:
            return 0


    def product_wise_lot(self):
        invoiced_lot_values = self._get_invoiced_lot_values()
        for invoiced_lot in invoiced_lot_values:
            lot_obj = self.env['stock.lot'].search([('id', '=', invoiced_lot['lot_id'])])
            if lot_obj and lot_obj.product_id:
                invoiced_lot['product_id'] = lot_obj.product_id.id
                invoiced_lot['expiration_date'] = lot_obj.expiration_date and lot_obj.expiration_date.strftime('%d-%m-%Y') or " "
            else:
                invoiced_lot['product_id'] = " "
                invoiced_lot['expiration_date'] = " "

        return invoiced_lot_values

    def sar_num2words(self, amount):
        text = num2words(amount, lang='en_IN')
        return text



class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def get_tax_details(self):
        taxes = {}
        all_tax = self.compute_all_tax
        for val, key in enumerate(all_tax):
            if 'tax_repartition_line_id' in key:
                if 'CGST' in all_tax[key]['name']:
                    taxes['CGST'] = {'name':'CGST',
                                  '%':all_tax[key]['name'].split(' ')[0],
                                  'amount': -all_tax[key]['balance']
                                  }
                elif 'SGST' in all_tax[key]['name']:
                    taxes['SGST'] = {'name':'SGST',
                                  '%':all_tax[key]['name'].split(' ')[0],
                                  'amount': -all_tax[key]['balance']
                                  }
                elif 'IGST' in all_tax[key]['name']:
                    taxes['IGST'] = {'name':'IGST',
                                  '%':all_tax[key]['name'].split(' ')[0],
                                  'amount': -all_tax[key]['balance']
                                  }
        return taxes