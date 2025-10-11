from odoo import fields, models, api
from collections import defaultdict
from num2words import num2words


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def get_tax_group(self, group=False):
        if group:
            tax_totals = self.tax_totals
            for taxes in tax_totals['groups_by_subtotal']['Untaxed Amount']:
                if taxes['tax_group_name'] == group:
                    return taxes['tax_group_amount']
        else:
            return 0


    def _get_delivered_lot_values(self):
        """ Get and prepare data to show a table of invoiced lot on the invoice's report. """
        self.ensure_one()
        result = []

        qties_per_lot = defaultdict(float)
        previous_qties_delivered = defaultdict(float)
        stock_move_lines = self.order_line.move_ids.move_line_ids.filtered(lambda sml: sml.state == 'done' and sml.lot_id).sorted(lambda sml: (sml.date, sml.id))
        for sml in stock_move_lines:
            product = sml.product_id
            product_uom = product.uom_id
            quantity = sml.product_uom_id._compute_quantity(sml.quantity, product_uom)

            # is it a stock return considering the document type (should it be it thought of as positively or negatively?)
            is_stock_return = (
                    (sml.location_id.usage, sml.location_dest_id.usage) == ('customer', 'internal')
            )
            if is_stock_return:
                returned_qty = min(qties_per_lot[sml.lot_id], quantity)
                qties_per_lot[sml.lot_id] -= returned_qty
                quantity = returned_qty - quantity


            qties_per_lot[sml.lot_id] += quantity

        for lot, qty in qties_per_lot.items():
            # access the lot as a superuser in order to avoid an error
            # when a user prints an invoice without having the stock access
            lot = lot.sudo()
            result.append({
                'product_name': lot.product_id.display_name,
                'uom_name': lot.product_uom_id.name,
                'lot_name': lot.name,
                # The lot id is needed by localizations to inherit the method and add custom fields on the invoice's report.
                'lot_id': lot.id,
                'product_id': lot.product_id.id,
                'expiration_date': lot.expiration_date.strftime('%d-%m-%Y'),
            })

        return result

    def sar_num2words(self, amount):
        text = num2words(amount, lang='en_IN')
        return text

