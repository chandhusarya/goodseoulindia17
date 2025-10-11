# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from collections import defaultdict
import pytz
from odoo.tools import float_is_zero

class AccountMove(models.Model):
    _inherit = 'account.move'

    shift_id = fields.Many2one('user.shift', 'Shift', copy=False, )

    def copy_data(self, default=None):
        res = super(AccountMove, self).copy_data(default=default)
        print(self._context)
        if self._context.get('sales_return_form_id', False):
            return_lines = self.env['sales.return.form'].browse(self._context['sales_return_form_id']).line_ids
            for index, val in zip(self, res):
                print(val)
                return_line = return_lines.filtered(lambda l: l.name == val.get('name', False))
                if not return_line:
                    # print(val)
                    # line_ids.po(index)
                    pass

                else:
                    first_return = return_lines[0]
                    val[2].update({
                        'quantity': first_return.product_uom_qty,
                        'package_id': first_return.product_packaging_id.id,
                        'product_packaging_qty': first_return.product_packaging_qty,
                        'pkg_unit_price': first_return.pkg_unit_price,
                        'price_unit': first_return.price_unit,
                    })

        return res

    def _stock_account_prepare_anglo_saxon_out_lines_vals(self):
        ''' Prepare values used to create the journal items (account.move.line) corresponding to the Cost of Good Sold
        lines (COGS) for customer invoices.

        Example:

        Buy a product having a cost of 9 being a storable product and having a perpetual valuation in FIFO.
        Sell this product at a price of 10. The customer invoice's journal entries looks like:

        Account                                     | Debit | Credit
        ---------------------------------------------------------------
        200000 Product Sales                        |       | 10.0
        ---------------------------------------------------------------
        101200 Account Receivable                   | 10.0  |
        ---------------------------------------------------------------

        This method computes values used to make two additional journal items:

        ---------------------------------------------------------------
        220000 Expenses                             | 9.0   |
        ---------------------------------------------------------------
        101130 Stock Interim Account (Delivered)    |       | 9.0
        ---------------------------------------------------------------

        Note: COGS are only generated for customer invoices except refund made to cancel an invoice.

        :return: A list of Python dictionary to be passed to env['account.move.line'].create.
        '''
        lines_vals_list = []
        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
        for move in self:
            # Make the loop multi-company safe when accessing models like product.product
            move = move.with_company(move.company_id)

            if not move.is_sale_document(include_receipts=True) or not move.company_id.anglo_saxon_accounting:
                continue

            for line in move.invoice_line_ids:

                # Filter out lines being not eligible for COGS.
                if not line._eligible_for_cogs():
                    continue

                # Retrieve accounts needed to generate the COGS.
                accounts = line.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=move.fiscal_position_id)
                debit_interim_account = accounts['stock_output']
                credit_expense_account = accounts['expense'] or move.journal_id.default_account_id
                if not debit_interim_account or not credit_expense_account:
                    continue

                # Compute accounting fields.
                sign = -1 if move.move_type == 'out_refund' else 1
                price_unit = line._stock_account_get_anglo_saxon_price_unit()
                fixed_discount, additional_discount = line._stock_account_get_discount(line.quantity)
                amount_currency = sign * line.quantity * price_unit

                if move.currency_id.is_zero(amount_currency) or float_is_zero(price_unit, precision_digits=price_unit_prec):
                    continue

                # Add interim account line.
                lines_vals_list.append({
                    'name': line.name[:64],
                    'move_id': move.id,
                    'partner_id': move.commercial_partner_id.id,
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_uom_id.id,
                    'quantity': line.quantity,
                    'price_unit': price_unit,
                    'amount_currency': -amount_currency,
                    'account_id': debit_interim_account.id,
                    'display_type': 'cogs',
                    'tax_ids': [],
                    'cogs_origin_id': line.id,
                })

                # Add expense account line.
                lines_vals_list.append({
                    'name': line.name[:64],
                    'move_id': move.id,
                    'partner_id': move.commercial_partner_id.id,
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_uom_id.id,
                    'quantity': line.quantity,
                    'price_unit': -price_unit,
                    'amount_currency': amount_currency,
                    'account_id': credit_expense_account.id,
                    'analytic_distribution': line.analytic_distribution,
                    'display_type': 'cogs',
                    'tax_ids': [],
                    'cogs_origin_id': line.id,
                    'fixed_discount': fixed_discount,
                    'additional_discount': additional_discount,
                })
        return lines_vals_list


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    sales_return_line_id = fields.Many2one('sales.return.form.line', string="Sales Return Line", copy=False)
    fixed_discount = fields.Float(
        string='Fixed Discount')
    additional_discount = fields.Float(
        string='Additional Discount')

    def _stock_account_get_anglo_saxon_price_unit(self):
        #This method is inherited to get correct cost on sales returns for anglo saxon accounting
        self.ensure_one()
        #Check this entry is part of sales return and get price account move generated for stock return
        if self.sales_return_line_id:
            unit_price = 0
            total_amount = 0
            stock_move = self.env['stock.move'].search([('sales_return_line_id', '=', self.sales_return_line_id.id)])
            print("sales_return_line :  ", self.sales_return_line_id.product_id.name, '  ::  ', self.sales_return_line_id.product_packaging_qty)
            for sm in stock_move:
                quantity = 0
                for am in sm.account_move_ids:
                    unit_price += am.amount_total
                    total_amount += am.amount_total

                for sm_line in sm.move_line_ids:
                    quantity += sm_line.quantity

                #print("unit_price : ", unit_price, " | quantity_done : ", sm.quantity_done)

                unit_price = unit_price/quantity


            print("\n\n\nUnit Price::==>> ", unit_price)
            print("Total Amount::==>> ", total_amount)
            print("quantity::==>> ", quantity)



            return unit_price
        return super(AccountMoveLine, self)._stock_account_get_anglo_saxon_price_unit()


    def _get_invoiced_lot_values_by_product_sales_return(self, product_id):
        """ Get and prepare data to show a table of invoiced lot on the invoice's report. """
        self.ensure_one()
        user_tz = self.env.context.get('tz')
        res = []
        if self.move_id.state == 'draft' or not self.move_id.invoice_date or self.move_id.move_type not in ('out_invoice', 'out_refund'):
            return res

        qties_per_lot = defaultdict(float)
        stock_move_lines = self.sale_line_ids.move_ids.move_line_ids.filtered(
            lambda sml: sml.state == 'done' and sml.lot_id).sorted(lambda sml: (sml.date, sml.id))

        for sml in stock_move_lines:
            if sml.location_id.usage == 'customer':
                continue
            product = sml.product_id
            product_uom = product.uom_id
            qty_done = sml.product_uom_id._compute_quantity(sml.quantity, product_uom)
            qties_per_lot[sml.lot_id, sml.location_id.id] += qty_done

        # Cha Change 12/10/2022
        for lot_location, qty in qties_per_lot.items():
            # Cha Change 12/10/2022
            lot, location_id = lot_location
            if lot.product_id.id == product_id:

                invoiced_lot_qty = qty
                expiry_date = False
                if lot.expiration_date:
                    expiry_date = pytz.UTC.localize(lot.expiration_date)
                    #expiry_date = expiry_date.astimezone(pytz.timezone(user_tz))

                res.append({
                    'product_name': lot.product_id.display_name,
                    'quantity': invoiced_lot_qty,
                    'uom_name': lot.product_uom_id.name,
                    'lot_name': lot.name,
                    'expiry': expiry_date.strftime("%d/%m/%Y, %H:%M:%S") if lot.expiration_date else False,
                    # The lot id is needed by localizations to inherit the method and add custom fields on the invoice's report.
                    'lot_id': lot.id,
                    'product_id': lot.product_id.id,
                    # Cha Change 12/10/2022
                    'location_id' : location_id,
                })

        return res

    def _stock_account_get_discount(self, quantity):
        so_line = self.sale_line_ids and self.sale_line_ids[-1] or False
        sales_return_line_id = self.sales_return_line_id or False
        print('so_line', so_line, 'sales_return_line_id', sales_return_line_id)
        '''
        Discount calculation for customer invoice and sales return with invoice.
        '''
        if so_line:
            fixed_discount, additional_discount = 0,0
            quantity_done = 0
            #Take original stock move only. Ignore return if any.
            for mv in so_line.move_ids.filtered(lambda l:l.picking_code == 'outgoing'):
                quantity_done += mv.quantity
                move_lines = mv.move_line_ids
                lots = move_lines.mapped('lot_id')
                print('move_lines', move_lines, 'lots', lots)
                if len(lots) > 0:
                    fixed_discount += (sum(lots.mapped('fixed_discount'))/len(lots)) * mv.quantity
                    additional_discount += (sum(lots.mapped('additional_discount'))/len(lots)) * mv.quantity
                    print('fixed_discount:', fixed_discount ,'additional_discount', additional_discount)
            '''
            If move line qty is not matching with stock move quantity, convert to actual qty.
            This is in case same item came twice under invoice line.
            '''
            if quantity_done != quantity:
                fixed_discount = (fixed_discount/quantity_done) * quantity
                additional_discount = (additional_discount/quantity_done) * quantity
            return round(fixed_discount, 2), round(additional_discount, 2)
        '''
        Discount calculation for sales return without invoice.
        '''
        if sales_return_line_id:
            fixed_discount, additional_discount = 0,0
            quantity_done = 0
            stock_move = self.env['stock.move'].search([('sales_return_line_id', '=', sales_return_line_id.id),
                                                        ('state', '=', 'done')])
            if not stock_move:
                #Some cases stock move got merged with move form same item
                #So we need to find stock of other sales return line
                sales_retun_lines = self.env['sales.return.form.line'].search([
                    ('parent_id', '=', sales_return_line_id.parent_id.id),
                    ('product_id', '=', sales_return_line_id.product_id.id),
                    ('id', '!=', sales_return_line_id.id)])
                for each_line in sales_retun_lines:
                    stock_move = self.env['stock.move'].search(
                        [('sales_return_line_id', '=', each_line.id),
                         ('state', '=', 'done')])
                    if stock_move:
                        break

            for mv in stock_move:
                quantity_done += mv.quantity
                move_lines = mv.move_line_ids
                lots = move_lines.mapped('lot_id')
                print('move_lines', move_lines, 'lots', lots)
                if len(lots) > 0:
                    fixed_discount += (sum(lots.mapped('fixed_discount'))/len(lots)) * mv.quantity
                    additional_discount += (sum(lots.mapped('additional_discount'))/len(lots)) * mv.quantity
                    print('fixed_discount:', fixed_discount ,'additional_discount', additional_discount)
            '''
            If move line qty is not matching with stock move quantity, convert to actual qty.
            This is in case same item came twice under credit note.
            '''
            if quantity_done != quantity:
                fixed_discount = (fixed_discount/quantity_done) * quantity
                additional_discount = (additional_discount/quantity_done) * quantity
            return round(fixed_discount, 2), round(additional_discount, 2)
        return 0, 0
