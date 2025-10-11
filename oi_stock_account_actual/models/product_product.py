'''
Created on Nov 18, 2019

@author: Zuhair Hammadi
'''
from odoo import models, fields, api, _
from odoo.tools import float_is_zero
from odoo.tools.float_utils import float_repr
from odoo.exceptions import UserError

class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    def _prepare_out_svl_vals_lot(self, quantity, company, lot_id):
        """Prepare the values for a stock valuation layer created by a delivery.

        :param quantity: the quantity to value, expressed in `self.uom_id`
        :return: values to use in a call to create
        :rtype: dict
        """
        print("\n\n\n\n****************************99999999999999999***************************")


        self.ensure_one()
        lot_id.ensure_one()
        # Quantity is negative for out valuation layers.
        quantity = -1 * quantity
        vals = {
            'product_id' : self.id,
            'value': quantity * self.standard_price,
            'unit_cost': self.standard_price,
            'quantity': quantity,
            'lot_id' : lot_id.id
        }
        print("self.cost_method ========>> ", self.cost_method)
        if self.cost_method in ('average', 'fifo'):
            fifo_vals = self._run_fifo_lot(abs(quantity), company, lot_id)
            vals['remaining_qty'] = fifo_vals.get('remaining_qty')
            # In case of AVCO, fix rounding issue of standard price when needed.
            if self.cost_method == 'average':
                currency = self.env.company.currency_id
                rounding_error = currency.round(self.standard_price * self.quantity_svl - self.value_svl)
                if rounding_error:
                    # If it is bigger than the (smallest number of the currency * quantity) / 2,
                    # then it isn't a rounding error but a stock valuation error, we shouldn't fix it under the hood ...
                    if abs(rounding_error) <= (abs(quantity) * currency.rounding) / 2:
                        vals['value'] += rounding_error
                        vals['rounding_adjustment'] = '\nRounding Adjustment: %s%s %s' % (
                            '+' if rounding_error > 0 else '',
                            float_repr(rounding_error, precision_digits=currency.decimal_places),
                            currency.symbol
                        )
            if self.cost_method == 'fifo':
                vals.update(fifo_vals)

        print("vals ======>> ", vals)


        return vals
    
    def _run_fifo_lot(self, quantity, company, lot_id):
        self.ensure_one()

        # Find back incoming stock valuation layers (called candidates here) to value `quantity`.
        qty_to_take_on_candidates = quantity
        candidates = self.env['stock.valuation.layer'].sudo().with_context(active_test=False).search([
            ('product_id', '=', self.id),
            ('remaining_qty', '>', 0),
            ('company_id', '=', company.id),
            ('lot_id','=', lot_id.id)
        ])



        print("\n\n\ncandidates =====>> ", candidates)
        print("product_id =====>> ", self.name)
        print("quantity =====>> ", quantity)
        print("company_id =====>> ", company.name)
        print("lot_id =====>> ", lot_id.name)

        new_standard_price = 0
        tmp_value = 0  # to accumulate the value taken on the candidates
        for candidate in candidates:
            qty_taken_on_candidate = min(qty_to_take_on_candidates, candidate.remaining_qty)

            print("candidate                 ==>> ", candidate)
            print("qty_taken_on_candidate    ==>> ", qty_taken_on_candidate)
            print("candidate.remaining_value ==>> ", candidate.remaining_value)
            print("candidate.remaining_qty   ==>> ", candidate.remaining_qty)

            candidate_unit_cost = candidate.remaining_value / candidate.remaining_qty

            print("candidate_unit_cost       ==>> ", candidate_unit_cost)

            new_standard_price = candidate_unit_cost
            value_taken_on_candidate = qty_taken_on_candidate * candidate_unit_cost
            value_taken_on_candidate = candidate.currency_id.round(value_taken_on_candidate)
            new_remaining_value = candidate.remaining_value - value_taken_on_candidate

            candidate_vals = {
                'remaining_qty': candidate.remaining_qty - qty_taken_on_candidate,
                'remaining_value': new_remaining_value,
            }
            candidate.write(candidate_vals)
            qty_to_take_on_candidates -= qty_taken_on_candidate
            tmp_value += value_taken_on_candidate
            if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
                break

        # Update the standard price with the price of the last used candidate, if any.
        if new_standard_price and self.cost_method == 'fifo':
            self.sudo().with_company(company).standard_price = new_standard_price

        # If there's still quantity to value but we're out of candidates, we fall in the
        # negative stock use case. We chose to value the out move at the price of the
        # last out and a correction entry will be made once `_fifo_vacuum` is called.
        vals = {}
        if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
            print("--------111111111111----------------222222222222--------")
            vals = {
                'value': -tmp_value,
                'unit_cost': tmp_value / quantity,
            }
            print("tmp_value =====", tmp_value)
            print("quantity ===== ", quantity)
            print("unit_cost ===== ", tmp_value / quantity)
        else:
            assert qty_to_take_on_candidates > 0
            last_fifo_price = new_standard_price or self.manual_cost_for_zero_cost_item

            if last_fifo_price < 0.0001:
                error_text = "1111111111 Couldn't find correct costing for lot %s, please apply sku wise costing in product master of %s" % (
                lot_id.name, self.name)
                raise UserError(_(error_text))


            negative_stock_value = last_fifo_price * -qty_to_take_on_candidates
            tmp_value += abs(negative_stock_value)
            vals = {
                'remaining_qty': -qty_to_take_on_candidates,
                'value': -tmp_value,
                'unit_cost': last_fifo_price,
            }
        print("Vals =====>> ", vals)
        return vals

    def _run_fifo_vacuum(self, company=None):
        """Chandhu Customisation, vacuum not considering the item lot id in valution layer"""

        """Compensate layer valued at an estimated price with the price of future receipts
        if any. If the estimated price is equals to the real price, no layer is created but
        the original layer is marked as compensated.

        :param company: recordset of `res.company` to limit the execution of the vacuum
        """
        self.ensure_one()
        if company is None:
            company = self.env.company
        svls_to_vacuum = self.env['stock.valuation.layer'].sudo().search([
            ('product_id', '=', self.id),
            ('remaining_qty', '<', 0),
            ('stock_move_id', '!=', False),
            ('company_id', '=', company.id),
        ], order='create_date, id')

        if not svls_to_vacuum:
            return

        as_svls = []

        domain = [
            ('company_id', '=', company.id),
            ('product_id', '=', self.id),
            ('remaining_qty', '>', 0),
            ('create_date', '>=', svls_to_vacuum[0].create_date),
        ]
        all_candidates = self.env['stock.valuation.layer'].sudo().search(domain)

        for svl_to_vacuum in svls_to_vacuum:
            # We don't use search to avoid executing _flush_search and to decrease interaction with DB
            candidates = all_candidates.filtered(
                lambda r: r.create_date >= svl_to_vacuum.create_date
                          and r.id > svl_to_vacuum.id and r.lot_id.id == svl_to_vacuum.lot_id.id
            )
            if not candidates:
                break
            qty_to_take_on_candidates = abs(svl_to_vacuum.remaining_qty)
            qty_taken_on_candidates = 0
            tmp_value = 0
            for candidate in candidates:
                qty_taken_on_candidate = min(candidate.remaining_qty, qty_to_take_on_candidates)
                qty_taken_on_candidates += qty_taken_on_candidate

                candidate_unit_cost = candidate.remaining_value / candidate.remaining_qty
                value_taken_on_candidate = qty_taken_on_candidate * candidate_unit_cost
                value_taken_on_candidate = candidate.currency_id.round(value_taken_on_candidate)
                new_remaining_value = candidate.remaining_value - value_taken_on_candidate

                candidate_vals = {
                    'remaining_qty': candidate.remaining_qty - qty_taken_on_candidate,
                    'remaining_value': new_remaining_value
                }
                candidate.write(candidate_vals)
                if not (candidate.remaining_qty > 0):
                    all_candidates -= candidate

                qty_to_take_on_candidates -= qty_taken_on_candidate
                tmp_value += value_taken_on_candidate
                if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
                    break

            # Get the estimated value we will correct.
            remaining_value_before_vacuum = svl_to_vacuum.unit_cost * qty_taken_on_candidates
            new_remaining_qty = svl_to_vacuum.remaining_qty + qty_taken_on_candidates
            corrected_value = remaining_value_before_vacuum - tmp_value
            svl_to_vacuum.write({
                'remaining_qty': new_remaining_qty,
            })

            # Don't create a layer or an accounting entry if the corrected value is zero.
            if svl_to_vacuum.currency_id.is_zero(corrected_value):
                continue

            corrected_value = svl_to_vacuum.currency_id.round(corrected_value)
            move = svl_to_vacuum.stock_move_id
            vals = {
                'product_id': self.id,
                'value': corrected_value,
                'unit_cost': 0,
                'quantity': 0,
                'remaining_qty': 0,
                'stock_move_id': move.id,
                'company_id': move.company_id.id,
                'description': 'Revaluation of %s (negative inventory)' % move.picking_id.name or move.name,
                'stock_valuation_layer_id': svl_to_vacuum.id,
                'lot_id' : svl_to_vacuum.lot_id and svl_to_vacuum.lot_id.id
            }
            vacuum_svl = self.env['stock.valuation.layer'].sudo().create(vals)

            if self.valuation != 'real_time':
                continue
            as_svls.append((vacuum_svl, svl_to_vacuum))

        # If some negative stock were fixed, we need to recompute the standard price.
        product = self.with_company(company.id)
        if product.cost_method == 'average' and not float_is_zero(product.quantity_svl,
                                                                  precision_rounding=self.uom_id.rounding):
            product.sudo().with_context(disable_auto_svl=True).write(
                {'standard_price': product.value_svl / product.quantity_svl})

        self.env['stock.valuation.layer'].browse(x[0].id for x in as_svls)._validate_accounting_entries()

        for vacuum_svl, svl_to_vacuum in as_svls:
            self._create_fifo_vacuum_anglo_saxon_expense_entry(vacuum_svl, svl_to_vacuum)
