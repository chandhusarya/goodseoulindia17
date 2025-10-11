# -*- coding: utf-8 -*-

from odoo import models, fields, _, api, SUPERUSER_ID
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_round, float_is_zero, groupby
from datetime import date

from datetime import datetime, timedelta,date
import time


class LpoWiseShipmentAllocation(models.Model):
    _name = 'lpo.wise.shipment.allocation'
    _description = 'LPO wise Shipment Allocation'
    _order = 'purchase_id asc'

    shipment_advice_id = fields.Many2one('shipment.advice', string='Shipment Advice')
    shipment_advice_line = fields.Many2one('shipment.advice.line', string='Line')
    shipment_advice_line_details = fields.Many2one('shipment.advice.line.details', string='Line Details')

    shipment_advice_summary = fields.Many2one('shipment.advice.summary', string='Summary')
    shipment_advice_summary_line = fields.Many2one('shipment.summary.line', string='Summary Line')

    purchase_id = fields.Many2one('purchase.order', string='PO')
    purchase_line_id = fields.Many2one('purchase.order.line', string='PO Line')

    shipment_advice_line_qty = fields.Float("Line Qty")
    shipment_advice_summary_line_qty = fields.Float("Summary Line Qty")



    def create_stock_moves(self, picking, mode, purchase_order, shipment_advice_id):
        # Creating stock moves for received items
        values = self.prepare_stock_moves(picking, mode, purchase_order, shipment_advice_id)
        if values:

            print("\n\ncreate_stock_moves ======>> ", values)
            print("\n\n")


            move = self.env['stock.move'].create(values)

            return move

        else:
            return False

    def prepare_stock_moves(self, picking, mode, purchase_order, shipment_advice_id):
        """ Prepare the stock moves data for one order line. This function returns a list of
        dictionary ready to be used in stock.move's create()
        """



        location_dest_id = picking.location_dest_id.id
        res_move_vals = []

        #Find allocation lines for this shipment advice and purchase order
        allocation = self.env['lpo.wise.shipment.allocation'].search([
            ('shipment_advice_id', '=', shipment_advice_id.id),
            ('purchase_id', '=', purchase_order.id)])

        #Group allocation under each po line
        purchase_line_wise = {}
        for alloc in allocation:
            if alloc.shipment_advice_summary_line_qty > 0:

                if not alloc.shipment_advice_summary_line:
                    raise UserError(_('Error in GRN, Please check with IT'))

                if alloc.purchase_line_id in purchase_line_wise:
                    purchase_line_wise[alloc.purchase_line_id].append(alloc)
                else:
                    purchase_line_wise[alloc.purchase_line_id] = [alloc]

        #Generate move line based on purchase line
        for purchase_line in purchase_line_wise:
            move_line_nosuggest = []
            mv_total_qty_received = 0
            purchase_line.move_dest_ids.purchase_line_id = False


            for alloc in purchase_line_wise[purchase_line]:

                shipment_advice_summary = alloc.shipment_advice_summary
                summary_line = alloc.shipment_advice_summary_line

                lot_id = summary_line.lot_id

                #Update Lot as per actual receiving
                if summary_line.lot_id:
                    summary_line.lot_id.expiration_date	= summary_line.expiry_date_actual
                    summary_line.lot_id.removal_date = summary_line.expiry_date_actual
                    summary_line.lot_id.use_date = summary_line.expiry_date_actual
                    summary_line.lot_id.alert_date = summary_line.expiry_date_actual

                else:
                    times = str(round(time.time() * 1000))[-2:]
                    line_id = str(alloc.id)
                    last_section = line_id[-4:]
                    if len(shipment_advice_summary.product_id.default_code) > 5:
                        sq_start = shipment_advice_summary.product_id.default_code[0:5] + times
                    sq_start += last_section.upper()
                    lot_name = sq_start

                    lot = self.env['stock.lot'].create({'name': lot_name,
                               'company_id': self.env.company.id,
                               'expiration_date': summary_line.expiry_date_actual,
                               'removal_date': summary_line.expiry_date_actual,
                               'use_date': summary_line.expiry_date_actual,
                               'alert_date': summary_line.expiry_date_actual,
                               'product_id': shipment_advice_summary.product_id.id})

                    lot._compute_product_expiry_alert()

                    print("lot =====>> ", lot)


                    summary_line.lot_id = lot.id



                print("summary_line.lot_id =====>> ", summary_line.lot_id)



                packaging_uom = shipment_advice_summary.product_packaging_id.product_uom_id
                qty_per_packaging = shipment_advice_summary.product_packaging_id.qty
                total_qty_received = alloc.shipment_advice_summary_line_qty

                #Convenrty packaging qty to uom qty
                total_qty_received = packaging_uom._compute_quantity(total_qty_received * qty_per_packaging, purchase_line.product_uom)
                product_uom_qty, product_uom = purchase_line.product_uom._adjust_uom_quantities(total_qty_received, shipment_advice_summary.product_id.uom_id)

                mv_total_qty_received = mv_total_qty_received + product_uom_qty

                # Creating lines against lot received
                move_line_nosuggest.append((0, 0,
                    {
                        'lot_id': summary_line.lot_id.id,
                        'picking_id': picking.id,
                        'product_id': purchase_line.product_id.id,
                        #'quantity_product_uom': product_uom_qty,
                        'quantity': product_uom_qty,
                        'lot_name': summary_line.lot_id.name,
                        'expiration_date': summary_line.expiry_date_actual,
                        'product_uom_id': product_uom.id,
                        'location_id': purchase_line.order_id.partner_id.property_stock_supplier.id,
                        'location_dest_id': location_dest_id
                    }))

            purchase_line._check_orderpoint_picking_type()
            price_unit = purchase_line._get_stock_move_price_unit()
            product = purchase_line.product_id.with_context(lang=purchase_line.order_id.dest_address_id.lang or self.env.user.lang)
            date_planned = purchase_line.date_planned or purchase_line.order_id.date_planned


            print("move_line_nosuggest ====>> ", move_line_nosuggest)

            move_vals = {
                'name': (purchase_line.name or '')[:2000],
                'product_id': purchase_line.product_id.id,
                'date': date_planned,
                'date_deadline': date_planned,
                'location_id': purchase_line.order_id.partner_id.property_stock_supplier.id,
                'location_dest_id': location_dest_id,
                'picking_id': picking.id,
                'partner_id': purchase_line.order_id.dest_address_id.id,
                'move_dest_ids': [(4, x) for x in purchase_line.move_dest_ids.ids],
                #'state': 'draft',
                'state': 'assigned',
                'purchase_line_id': purchase_line.id,
                'company_id': purchase_line.order_id.company_id.id,
                'price_unit': price_unit,
                'picking_type_id': purchase_line.order_id.picking_type_id.id,
                'group_id': purchase_line.order_id.group_id.id,
                'origin': purchase_line.order_id.name,
                'description_picking': product.description_pickingin or purchase_line.name,
                'propagate_cancel': purchase_line.propagate_cancel,
                'warehouse_id': purchase_line.order_id.picking_type_id.warehouse_id.id,
                'product_uom_qty': product_uom_qty,
                'product_uom': product_uom.id,
                'product_packaging_id': purchase_line.product_packaging_id.id,
                'pkg_demand': mv_total_qty_received,
                'pkg_done': mv_total_qty_received,
                'move_line_ids': move_line_nosuggest
            }
            res_move_vals.append(move_vals)

        return res_move_vals

    def _prepare_invoice(self, purchase_order, bl):
        """Prepare the dict of values to create the new invoice for a purchase order.
        """
        move_type = 'in_invoice'

        partner_invoice_id = purchase_order.partner_id.address_get(['invoice'])['invoice']

        ref = bl.name
        if bl.boe_number:
            ref = "%s %s" % (ref, bl.boe_number)

        invoice_vals = {
            'ref': ref,
            'move_type': move_type,
            'narration': bl.notes,
            'currency_id': purchase_order.currency_id.id,
            'invoice_user_id': self.env.user.id,
            'partner_id': partner_invoice_id,
            'payment_reference': ref,
            'partner_bank_id': purchase_order.partner_id.bank_ids[:1].id,
            'invoice_origin':  bl.name,
            'invoice_payment_term_id': purchase_order.payment_term_id.id,
            'invoice_line_ids': [],
            'company_id': bl.company_id.id,
            'invoice_date': bl.bl_date,
            'date': date.today(),
        }
        return invoice_vals


    def bill_create_invoice(self, purchase_order, shipment_advice, is_last_po):

        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        moves = self.env['account.move']

        shipment_advice_ref = shipment_advice[0].bl_entry_id.name
        invoice_vals = self._prepare_invoice(purchase_order, shipment_advice[0].bl_entry_id)
        invoice_vals["invoice_origin"] = shipment_advice_ref
        invoice_vals["shipment_bill_number"] = shipment_advice[0].bl_entry_id.name

        allocation = self.env['lpo.wise.shipment.allocation'].search([('shipment_advice_id', 'in', shipment_advice.ids),
                                                                      ('purchase_id', '=', purchase_order.id)])

        po_line_vals = {}
        po_line_foc = []
        for alloc in allocation:

            shipment_advice_summary = alloc.shipment_advice_summary

            packaging_uom = shipment_advice_summary.product_packaging_id.product_uom_id
            qty_per_packaging = shipment_advice_summary.product_packaging_id.qty

            # Line for Normal Qty
            #
            #
            qty_to_invoice = alloc.shipment_advice_summary_line_qty
            shipment_advice_summary_line_qty = alloc.shipment_advice_summary_line_qty
            foc_qty = alloc.shipment_advice_line_details.foc_qty

            if is_last_po == True and alloc.purchase_line_id.id not in po_line_foc:
                qty_to_invoice = qty_to_invoice - foc_qty
                shipment_advice_summary_line_qty = shipment_advice_summary_line_qty - foc_qty
                po_line_foc.append(alloc.purchase_line_id.id)

            qty_to_invoice = packaging_uom._compute_quantity(qty_to_invoice * qty_per_packaging,
                                                             alloc.purchase_line_id.product_uom)
            product_uom_qty, product_uom = alloc.purchase_line_id.product_uom._adjust_uom_quantities(
                qty_to_invoice, shipment_advice_summary.product_id.uom_id)



            if alloc.purchase_line_id.id not in po_line_vals:
                line_vals = self._prepare_account_move_line(alloc.purchase_line_id,
                                                shipment_advice_summary.product_packaging_id,
                                                product_uom_qty, shipment_advice_summary_line_qty)
                po_line_vals[alloc.purchase_line_id.id] = line_vals
            else:
                po_line_vals[alloc.purchase_line_id.id]['quantity'] += product_uom_qty
                po_line_vals[alloc.purchase_line_id.id]['product_packaging_qty'] += shipment_advice_summary_line_qty

            # Line for FOC Qty
            # We are creating a sperate line for foc
            #
            if foc_qty > 0 and is_last_po:

                qty_to_invoice = packaging_uom._compute_quantity(foc_qty * qty_per_packaging,
                                                                 alloc.purchase_line_id.product_uom)
                product_uom_qty, product_uom = alloc.purchase_line_id.product_uom._adjust_uom_quantities(
                    qty_to_invoice, shipment_advice_summary.product_id.uom_id)
                if alloc.purchase_line_id.id * 999 not in po_line_vals:
                    line_vals = self._prepare_account_move_line(alloc.purchase_line_id,
                                                                shipment_advice_summary.product_packaging_id,
                                                                product_uom_qty, foc_qty)
                    line_vals['product_id'] = False
                    line_vals['name'] = "FOC : " + line_vals['name']
                    po_line_vals[alloc.purchase_line_id.id * 999] = line_vals

        for po_line_id in po_line_vals:
            invoice_vals['invoice_line_ids'].append((0, 0, po_line_vals[po_line_id]))

        invoice = moves.create(invoice_vals)
        invoice.apply_po_discount()
        invoice.action_post()

        shipment_advice.write({'invoice_ids': [(4, invoice.id)]})

        if invoice.po_discount_entry_id:
            invoice.po_discount_entry_id.ref = moves.name
            invoice.po_discount_entry_id.action_post()

        # Update invoice reference in the system
        shipment_advice.invoice_id = invoice.id
        shipment_advice.is_invoiced = 'invoiced'

        mail_template = self.env.ref('kg_sarya_inventory.user_mail_template')
        mail_template.send_mail(invoice.id, force_send=True)

        # Posting Additional discount directly form method button_receive_stock_and_generate_bill_warehouse



    def bill_create_invoice_bl_wise(self, bl, shipment_advice):

        if not bl.l10n_in_gst_treatment:
            raise UserError("GST Treatment detail missing!")

        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        moves = self.env['account.move']

        shipment_advice_ref = bl.name

        purchase_order = bl.purchase_ids[0]

        invoice_vals = self._prepare_invoice(purchase_order, bl)
        invoice_vals["invoice_origin"] = shipment_advice_ref
        invoice_vals["shipment_bill_number"] = bl.name
        invoice_vals["l10n_in_gst_treatment"] = bl.l10n_in_gst_treatment

        allocation = self.env['lpo.wise.shipment.allocation'].search([('shipment_advice_id', 'in', shipment_advice.ids)])

        product_wise_vals = {}
        foc_details = []

        # Line for Normal Qty
        #
        for alloc in allocation:


            shipment_advice_summary = alloc.shipment_advice_summary

            packaging_uom = shipment_advice_summary.product_packaging_id.product_uom_id
            qty_per_packaging = shipment_advice_summary.product_packaging_id.qty

            qty_to_invoice = alloc.shipment_advice_summary_line_qty
            shipment_advice_summary_line_qty = alloc.shipment_advice_summary_line_qty

            # ****************************************
            #
            # Finding any FOC based on the bl line details
            # Because allocation line can be repeated for a bl line detail, based on number po are selected for the item
            foc_qty = alloc.shipment_advice_line_details.foc_qty
            if foc_qty > 0 and alloc.shipment_advice_line_details.id not in foc_details:

                #Deduction qty for the normal items. Foc items will be added as seperate line
                qty_to_invoice = qty_to_invoice - foc_qty
                shipment_advice_summary_line_qty = shipment_advice_summary_line_qty - foc_qty

                product_uom_qty = packaging_uom._compute_quantity(foc_qty * qty_per_packaging,
                                                          alloc.purchase_line_id.product_uom)
                #product_uom_qty, product_uom = alloc.purchase_line_id.product_uom._adjust_uom_quantities(
                #    foc_qty, shipment_advice_summary.product_id.uom_id)


                line_vals = self._prepare_account_move_line(alloc.purchase_line_id,
                                                            shipment_advice_summary.product_packaging_id,
                                                            product_uom_qty, foc_qty)
                line_vals['product_id'] = False
                line_vals['name'] = "FOC : " + line_vals['name']

                #Find stock in out account for foc entry, not the default account of the journal
                category = self.env['product.category'].search([('name', '=', 'Dry')], limit=1)
                line_vals['account_id'] = category.property_stock_account_input_categ_id.id

                product_wise_vals[alloc.shipment_advice_line_details.id] = line_vals

                foc_details.append(alloc.shipment_advice_line_details.id)





            # ****************************************
            #
            # Processing All received Qty
            qty_to_invoice = packaging_uom._compute_quantity(qty_to_invoice * qty_per_packaging,
                                                             alloc.purchase_line_id.product_uom)
            product_uom_qty, product_uom = alloc.purchase_line_id.product_uom._adjust_uom_quantities(
                qty_to_invoice, shipment_advice_summary.product_id.uom_id)



            if alloc.purchase_line_id.product_id.id not in product_wise_vals:
                line_vals = self._prepare_account_move_line(alloc.purchase_line_id,
                                                shipment_advice_summary.product_packaging_id,
                                                product_uom_qty, shipment_advice_summary_line_qty)

                print("\n\n\nline_vals ==>>", line_vals)

                product_wise_vals[alloc.purchase_line_id.product_id.id] = line_vals
            else:
                product_wise_vals[alloc.purchase_line_id.product_id.id]['quantity'] += product_uom_qty
                product_wise_vals[alloc.purchase_line_id.product_id.id]['product_packaging_qty'] += shipment_advice_summary_line_qty







        for key in product_wise_vals:
            invoice_vals['invoice_line_ids'].append((0, 0, product_wise_vals[key]))
        print('invoice_vals----------', invoice_vals)
        invoice = moves.create(invoice_vals)
        invoice.apply_po_discount()
        invoice.action_post()

        shipment_advice.write({'invoice_ids': [(4, invoice.id)]})

        if invoice.po_discount_entry_id:
            invoice.po_discount_entry_id.ref = moves.name
            invoice.po_discount_entry_id.action_post()

        # Update invoice reference in the system
        shipment_advice.invoice_id = invoice.id
        shipment_advice.is_invoiced = 'invoiced'

        #Updating bl
        bl.write({'invoice_ids': [(4, invoice.id)]})

        mail_template = self.env.ref('kg_sarya_inventory.user_mail_template')
        mail_template.send_mail(invoice.id, force_send=True)

        # Posting Additional discount directly form method button_receive_stock_and_generate_bill_warehouse


    def post_additional_discount(self, invoice, shipment_advice, purchase_order):

        allocation = self.env['lpo.wise.shipment.allocation'].search([('shipment_advice_id', '=', shipment_advice.id),
                                                                      ('purchase_id', '=', purchase_order.id)])

        print("\n\n\nPurchase_order ==>> ", purchase_order.name)

        po_line_vals = {}
        for alloc in allocation:



            qty_to_invoice = alloc.shipment_advice_summary_line_qty



            amount = alloc.shipment_advice_line.additional_discount

            if alloc.purchase_line_id.id not in po_line_vals:

                po_line_vals[alloc.purchase_line_id.id] = {
                    'qty_to_invoice' : qty_to_invoice,
                    'amount' : amount,
                    'name' : "Additional Discount %s %s %s %s %s" % (str(purchase_order.name),
                                                               str(alloc.purchase_line_id.name),
                                                               str(shipment_advice.bill_no),
                                                               str(shipment_advice.name),
                                                               str(invoice.name))
                }

            else:
                po_line_vals[alloc.purchase_line_id.id]['qty_to_invoice'] += qty_to_invoice


        print("po_line_vals ===>> ", po_line_vals)

        if po_line_vals:
            move_obj = self.env['account.move']
            move_line_vals = []
            for po_line in po_line_vals:
                disc_vals = po_line_vals[po_line]

                amount = disc_vals['amount'] * disc_vals['qty_to_invoice']

                journal_entry = (0, 0, {
                    'account_id': shipment_advice.debit_acc_additional_disc.id,
                    'partner_id': purchase_order.partner_id.id,
                    'name': disc_vals['name'],
                    'debit': amount,
                })
                move_line_vals.append(journal_entry)

                journal_entry = (0, 0, {
                    'account_id': shipment_advice.credit_acc_additional_disc.id,
                    'partner_id': purchase_order.partner_id.id,
                    'name': disc_vals['name'],
                    'credit': amount,
                })
                move_line_vals.append(journal_entry)

            ref = "Additional Discount %s %s %s %s" % (str(purchase_order.name),
                                                       str(shipment_advice.bill_no),
                                                       str(shipment_advice.name),
                                                       str(invoice.name))
            create_entry = move_obj.create({
                'ref': ref,
                'partner_id': purchase_order.partner_id.id,
                'invoice_date': fields.Date.today(),
                'line_ids': move_line_vals,
                'journal_id' : shipment_advice.journal_additional_disc.id
                })
            create_entry.action_post()

            shipment_advice.write({'additional_discounts': [(4, create_entry.id)]})



    def _prepare_account_move_line(self, po_line=False, product_packaging_id=False, qty_to_invoice=0, product_packaging_qty=0):

        #Correct this unit price to take from
        aml_currency = po_line.currency_id
        date = fields.Date.today()
        res = {
            'display_type': po_line.display_type or 'product',
            'sequence': po_line.sequence,
            'name': '%s: %s' % (po_line.order_id.name, po_line.name),
            'product_id': po_line.product_id.id,
            'product_uom_id': po_line.product_uom.id,
            'quantity': qty_to_invoice,
            'price_unit': po_line.currency_id._convert(po_line.price_unit, aml_currency, po_line.company_id, date, round=False),
            'tax_ids': [(6, 0, po_line.taxes_id.ids)],
            #'analytic_account_id': po_line.account_analytic_id.id,
            #'analytic_tag_ids': [(6, 0, po_line.analytic_tag_ids.ids)],
            'purchase_line_id': po_line.id,
            'package_id': product_packaging_id.id,
            'product_packaging_qty': product_packaging_qty,
            'pkg_unit_price': po_line.pkg_unit_price,
            'account_id': po_line.product_id.categ_id.property_stock_account_input_categ_id.id
        }
        print('Res', res)
        return res
