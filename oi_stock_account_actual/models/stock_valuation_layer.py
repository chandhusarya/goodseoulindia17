'''
Created on Oct 6, 2021

@author: Zuhair Hammadi
'''
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero

class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    lot_id = fields.Many2one('stock.lot', 'Lot/Serial Number')

    @api.model_create_multi
    @api.returns('self', lambda value:value.id)
    def create(self, vals_list):

        for vals in vals_list:
            print("vals ==========>> ", vals)
            product = self.env['product.product'].browse(vals['product_id'])
            if product.detailed_type == 'product':
                if product.tracking != 'lot':
                    raise ValidationError(_('You cannot assign a Lot/Serial Number to a product that is not tracked by lot/serial number (%s).') % (product.name,))
                if product.categ_id.property_valuation != 'real_time':
                    raise ValidationError(_('Wrong configuration of the product category for product %s. You cannot '
                                            'create a stock valuation layer for a product whose category does not have '
                                            'real time valuation.') % (product.name,))

            if not vals.get('lot_id') and self.env['product.product'].browse(vals['product_id']).cost_level == 'lot' and 'stock_move_id' in vals:
                vals['lot_id'] = self.env['stock.move'].browse(vals['stock_move_id']).lot_id.id
            elif not vals.get('lot_id') and self.env['product.product'].browse(vals['product_id']).cost_level == 'lot':
                raise ValidationError(_('Missing required Lot/Serial Number'))
                # vals['lot_id'] = self.env['stock.lot'].search([('product_id', '=', vals['product_id']), ('company_id', '=', self.env.company.id)], order='id desc', limit=1).id


        return super(StockValuationLayer, self).create(vals_list)
    
    #@api.constrains('lot_id', 'product_id')
    def _check_lot_id(self):
        for record in self:
            if record.product_id.cost_level == 'lot' and not record.lot_id:
                raise ValidationError(_('Missing required Lot/Serial Number'))



    def correct_cost_of_empty_lot(self):

        valuation = self.search([('lot_id', '=', False)])

        for val in valuation:

            
            if val.lot_id:
                continue






    def correct_cost(self):

       valuation = self.search([('lot_id', '=', self.lot_id.id)])
       for rec in valuation:

            if rec.lot_id.id:
                final_cost = rec.lot_id.final_cost


                if final_cost > 0:



                    if rec.quantity > 0:
                        print("rec.reference", rec.reference)
                        if 'WH/IN/' in rec.reference or 'SLL/IN/' in rec.reference or 'Good /POS2/' in rec.reference:

                            rec.write({'remaining_value': final_cost * rec.remaining_qty})

                            # account_move_id = rec.account_move_id
                            # for move_line in account_move_id.line_ids:
                            #     if move_line.account_id.name == 'INVENTORY ON HAND':
                            #         final_cost_value = final_cost * rec.quantity
                            #         self.env.cr.execute("""
                            #             UPDATE account_move_line
                            #             SET debit = %s,
                            #                 credit = 0
                            #             WHERE id = %s
                            #         """, (final_cost_value, move_line.id))
                            #     else:
                            #         final_debit = final_cost * rec.quantity
                            #         self.env.cr.execute("""
                            #             UPDATE account_move_line
                            #             SET debit = 0,
                            #                 credit = %s
                            #             WHERE id = %s
                            #         """, (final_debit, move_line.id))

                        else:
                            rec.write({'remaining_value': final_cost * rec.remaining_qty,
                                       'unit_cost': final_cost,
                                       'value': final_cost * rec.quantity
                                       })

                            account_move_id = rec.account_move_id
                            for move_line in account_move_id.line_ids:
                                if move_line.account_id.name == 'INVENTORY ON HAND':
                                    final_cost_value = final_cost * rec.quantity
                                    self.env.cr.execute("""
                                                                    UPDATE account_move_line
                                                                    SET debit = %s,
                                                                        credit = 0
                                                                    WHERE id = %s
                                                                """, (final_cost_value, move_line.id))
                                else:
                                    final_debit = final_cost * rec.quantity
                                    self.env.cr.execute("""
                                                                    UPDATE account_move_line
                                                                    SET debit = 0,
                                                                        credit = %s
                                                                    WHERE id = %s
                                                                """, (final_debit, move_line.id))

                    if rec.quantity < 0:

                        rec.write({'unit_cost': final_cost, 'value': final_cost * rec.quantity})
                        account_move_id = rec.account_move_id
                        for move_line in account_move_id.line_ids:
                             if move_line.account_id.name == 'INVENTORY ON HAND':
                                 final_cost_value = final_cost * rec.quantity * -1
                                 self.env.cr.execute("""
                                     UPDATE account_move_line
                                     SET debit = 0,
                                         credit = %s
                                     WHERE id = %s
                                 """, (final_cost_value, move_line.id))
                             else:
                                 final_debit = final_cost * rec.quantity * -1
                                 self.env.cr.execute("""
                                     UPDATE account_move_line
                                     SET debit = %s,
                                         credit = 0
                                     WHERE id = %s
                                 """, (final_debit, move_line.id))






class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'


    def _apply_price_difference(self):
        svl_vals_list = []
        aml_vals_list = []
        for line in self:
            line = line.with_company(line.company_id)
            po_line = line.purchase_line_id
            uom = line.product_uom_id or line.product_id.uom_id

            # Don't create value for more quantity than received
            quantity = po_line.qty_received - (po_line.qty_invoiced - line.quantity)
            quantity = max(min(line.quantity, quantity), 0)
            if float_is_zero(quantity, precision_rounding=uom.rounding):
                continue

            layers = line._get_valued_in_moves().stock_valuation_layer_ids.filtered(lambda svl: svl.product_id == line.product_id and not svl.stock_valuation_layer_id)
            if not layers:
                continue

            new_svl_vals_list, new_aml_vals_list = line._generate_price_difference_vals(layers)
            svl_vals_list += new_svl_vals_list
            aml_vals_list += new_aml_vals_list

        print("\n\n\nsvl_vals_list ========>> ", svl_vals_list)
        print("\n\naml_vals_list ========>> ", aml_vals_list)
        return self.env['stock.valuation.layer'].sudo().create([]), self.env['account.move.line'].sudo().create([])
            