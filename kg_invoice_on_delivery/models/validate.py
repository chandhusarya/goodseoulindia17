from datetime import date

from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class InvoicePaymentWizard(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'
    _description = 'Invoice payment on delivery'

    advance_payment_method_delivered = fields.Selection([
        ('delivered', 'Regular invoice'),
    ], string='Create Invoice', default='delivered', required=True,
        help="A standard invoice is issued with all the order lines ready for invoicing, \
        according to their invoicing policy (based on ordered or delivered quantity).")


class StockPickingInv(models.Model):
    _inherit = "stock.picking"

    # create invoice on delivery
    def create_invoice_on_delivery(self):
        # picking_id = self.env['stock.picking'].browse(self._context.get('active_ids', []))
        picking_id = self
        sale_orders = self.env['sale.order'].search([('name', '=', picking_id.origin)])
        rebate_acc = False
        if sale_orders.partner_id.bill_type == 'bill_to_bill':
            invoice = self.env['account.move'].search(
                [('partner_id', '=', sale_orders.partner_id.id), ('move_type', '=', 'out_invoice')])
            for inv in invoice:
                if inv.payment_state == 'not_paid' and False:
                    raise UserError(_('There are unpaid Invoices for the Customer.'))
        # if self.advance_payment_method == 'delivered':
        # print("sale_orders------>>",sale_orders)
        inv = sale_orders._create_invoices(final=True)
        picking_id.invoice_status = 1
        # picking_id.delivery_status = 'invoiced'
        picking_id.invoice_id = inv.id
        inv.l10n_in_gst_treatment = inv.partner_id.l10n_in_gst_treatment
        inv.do_number = picking_id.name
        inv.action_post()

    def calculate_progressive_rebate(self, rebate, sale_order_total, partner, sale_order, child_partner, inv):
        """Calcuate progressive rebate"""
        account_move_obj = self.env['account.move'].sudo()
        progressive_rebate_obj = self.env['rebate.progressive.item'].sudo()
        company_id = self.env.company
        pricelist_item = self.env['product.pricelist'].search([('rebate_ids', '=', rebate.id)])
        journal_id = self.env['ir.config_parameter'].sudo().get_param('kg_sarya_rebate.rebate_journal_id')
        provision_acc = self.env['ir.config_parameter'].sudo().get_param('kg_sarya_rebate.rebate_provision_account_id')
        # print('provision_acc', int(provision_acc))
        if not journal_id and not provision_acc:
            raise UserError(_("Please configure Rebate journal and Rebate provision account from settings"))
        cr = self._cr
        product_list = []
        cust_list = []
        for prlist in pricelist_item:
            for item in prlist.item_ids:
                product = self.env['product.product'].search([('product_tmpl_id', '=', item.product_tmpl_id.id)])
                for prd in product:
                    product_list.append(prd.id)
            # for cust in prlist.customer_ids:
            #     cust_list.append(cust)
        cust_list.append(partner)
        products = tuple(product_list)
        for customer in cust_list:
            ledger_list = []
            child_list = []
            total = 0.0
            amount = 0.0
            rebate_applied = 0.0
            slab_reach = 0.0
            target_rebate = 0.0
            price_list = pricelist_item.ids
            r_type = ""
            # getting the total sale of the customer
            realtime_obj = self.env['prg.rebate.realtime'].search(
                [('rebate_id', '=', rebate.id), ('partner_id', '=', customer.id), ('state', '=', 'posted')])
            previous_total = sum(realtime_obj.mapped('current_sale_amount'))
            amount = previous_total + sale_order_total
            # for child customer getting the parent and other child to get total sale
            # if child_partner:
            #     child = self.env['res.partner'].search([('parent_partner_id','=',parent.id)])
            #     for ch in child:
            #         child_list.append(ch.id)
            #     child_list.append(parent.id)
            #     cr.execute(
            #         "select sum(sl.qty_delivered) as qty,sl.price_unit,sl.product_id from sale_order s left join sale_order_line sl on s.id= sl.order_id where s.date_order::date<='" + str(
            #             rebate.date_end) + "' and s.date_order::date>= '" + str(
            #             rebate.date_start) + "' and sl.product_id in" + str(
            #             products) +
            #         "and s.partner_id in %s and s.pricelist_id in %s and sl.qty_delivered >0"
            #         "group by sl.product_id,sl.price_unit", (tuple(child_list), tuple(price_list)))
            # # for parent customer only that customer need to be consider
            # else:
            #     cr.execute(
            #         "select sum(sl.qty_delivered) as qty,sl.price_unit,sl.product_id from sale_order s left join sale_order_line sl on s.id= sl.order_id where s.date_order::date<='" + str(
            #             rebate.date_end) + "' and s.date_order::date>= '" + str(
            #             rebate.date_start) + "' and sl.product_id in" + str(
            #             products) +
            #         "and s.partner_id = %s and s.pricelist_id in %s and sl.qty_delivered >0"
            #         "group by sl.product_id,sl.price_unit", (customer.id, tuple(price_list)))
            # product_dtls = cr.dictfetchall()
            # # finding total sales value of product which can apply rebate
            # for prd in product_dtls:
            #     amount = amount + (prd['qty'] * prd['price_unit'])
            prgrsv_items = self.env['rebate.progressive.item'].search(
                [('rebate_id', '=', rebate.id)], order='percentage desc')
            if len(prgrsv_items) > 0:
                total = 0
                prv_type = ''
                for prg in prgrsv_items:
                    if amount >= (prg.target_val):
                        total = total + ((prg.rebate_percentage / 100) * sale_order_total)
                        rebate_applied = prg.rebate_percentage
                        rebate_acc = prg.account_id.id
                        slab_reach = prg.rebate_percentage
                        r_type = 'match'
                        target_rebate = ((prg.rebate_percentage / 100) * prg.target_val)
                        break
                # checking if rebate percentage not achived yet then apply large rebate
                if total == 0:
                    # no slab reached so applying largest slab
                    prgrsv_large = self.env['rebate.progressive.item'].search(
                        [('rebate_id', '=', rebate.id)], order='percentage desc',
                        limit=1)
                    for el in prgrsv_large:
                        rebate_applied = el.rebate_percentage
                        total = (el.rebate_percentage / 100) * sale_order_total
                        rebate_acc = el.account_id.id
                        r_type = 'large'
                else:
                    # slab reached so checking the previous entries
                    prv_entry = self.env['prg.rebate.realtime'].search(
                        [('rebate_id', '=', rebate.id), ('partner_id', '=', customer.id)])
                    reverse_amount = 0.0
                    for entr in prv_entry:
                        # if previous entris rebate applied is grater than current rebate percentage then calulating reverse entry
                        if entr.rebate_applied > rebate_applied:
                            reverse_rebate = entr.rebate_applied - rebate_applied
                            reverse_amount = reverse_amount + ((reverse_rebate / 100) * entr.current_sale_amount)
                            prv_type = 'reverse'
                            entr.rebate_updated = rebate_applied
                            # if previous entris rebate applied is less than current rebate percentage then calulating  entry for previous
                        elif entr.rebate_updated < rebate_applied:
                            reverse_rebate = rebate_applied - entr.rebate_updated
                            reverse_amount = reverse_amount + ((reverse_rebate / 100) * entr.current_sale_amount)
                            new_applied = entr.rebate_updated + reverse_rebate
                            entr.rebate_updated = new_applied
                            prv_type = 'credit'
                    if len(prv_entry) > 0:
                        # creating reverse entry for the previous entries(case:rebate applied greater than current rebate)
                        if prv_type == 'reverse':
                            move_lines = []
                            crd_line = {}
                            crd_line['credit'] = reverse_amount
                            crd_line['partner_id'] = customer.id if customer else False
                            crd_line['account_id'] = rebate_acc
                            crd_tuple = (0, 0, crd_line)
                            move_lines.append(crd_tuple)
                            dbt_line = {}
                            dbt_line['debit'] = reverse_amount
                            dbt_line['account_id'] = int(provision_acc)
                            dbt_line['partner_id'] = customer.id if customer else False
                            dbt_tuple = (0, 0, dbt_line)
                            move_lines.append(dbt_tuple)
                            move = self.env['account.move'].create(
                                {'partner_id': customer.id, 'payment_reference': 'Rebate',
                                 'rebate_master_id': rebate.id, 'ref': '%s -%s' % (rebate.name, inv.name),
                                 'name': '/', 'journal_id': int(journal_id), 'date': date.today(),
                                 'invoice_date': date.today(), 'enty_type': 'reverse',
                                 'line_ids': move_lines, 'rebate_type': 'progressive',
                                 'sale_order_id': sale_order.id,
                                 'sale_order_customer_id': child_partner.id, })
                            move.action_post()
                        # creating credit entry for the previous entries(case:rebate applied less than current rebate)
                        if prv_type == 'credit':
                            move_lines = []
                            dbt_line = {}
                            dbt_line['debit'] = reverse_amount
                            dbt_line['partner_id'] = customer.id if customer else False
                            dbt_line['account_id'] = rebate_acc
                            dbt_tuple = (0, 0, dbt_line)
                            move_lines.append(dbt_tuple)
                            crd_line = {}
                            crd_line['credit'] = reverse_amount
                            crd_line['account_id'] = int(provision_acc)
                            crd_line['partner_id'] = customer.id if customer else False
                            crd_tuple = (0, 0, crd_line)
                            move_lines.append(crd_tuple)
                            move = self.env['account.move'].create(
                                {'partner_id': customer.id, 'payment_reference': 'Rebate',
                                 'rebate_master_id': rebate.id, 'ref': '%s -%s' % (rebate.name, inv.name),
                                 'name': '/', 'journal_id': int(journal_id), 'date': date.today(),
                                 'invoice_date': date.today(), 'enty_type': 'reverse',
                                 'line_ids': move_lines, 'rebate_type': 'progressive',
                                 'sale_order_id': sale_order.id,
                                 'sale_order_customer_id': child_partner.id, })
                            move.action_post()
            # execute if rebate slab reached or largest is applied
            if total > 0:
                # if slab reached then creating a rebate entry with currently reached slab percentage(prv_type is used to check that this sale is not after the largest slab reached)
                if r_type == 'match' and prv_type != '':
                    move_lines = []
                    dbt_line = {}
                    dbt_line['debit'] = target_rebate
                    dbt_line['partner_id'] = customer.id if customer else False
                    dbt_line['account_id'] = int(provision_acc)
                    det_tuple = (0, 0, dbt_line)
                    move_lines.append(det_tuple)
                    crd_line = {}
                    crd_line['credit'] = target_rebate
                    crd_line['account_id'] = int(customer.property_account_receivable_id.id)
                    crd_line['partner_id'] = customer.id if customer else False
                    crd_tuple = (0, 0, crd_line)
                    move_lines.append(crd_tuple)
                    journal_id = self.env['ir.config_parameter'].sudo().get_param(
                        'kg_sarya_rebate.rebate_journal_id') or False
                    if not journal_id:
                        raise UserError(_("Please configure Rebate journal from settings"))
                    move = self.env['account.move'].create(
                        {'partner_id': customer.id, 'payment_reference': 'Rebate', 'rebate_master_id': rebate.id,
                         'ref': '%s -%s' % (rebate.name, inv.name), 'name': '/',
                         'journal_id': int(journal_id), 'enty_type': 'normal', 'sale_amount': sale_order_total,
                         'rebate_type': 'progressive', 'rebate_applied': rebate_applied, 'date': date.today(),
                         'invoice_date': date.today(), 'line_ids': move_lines,
                         'sale_order_id': sale_order.id,
                         'sale_order_customer_id': child_partner.id, })
                    move.action_post()
                # creating a entry in provision account for the current sale amount
                move_lines = []
                dbt_line = {}
                dbt_line['debit'] = total
                dbt_line['partner_id'] = customer.id if customer else False
                dbt_line['account_id'] = rebate_acc
                det_tuple = (0, 0, dbt_line)
                move_lines.append(det_tuple)
                crd_line = {}
                crd_line['credit'] = total
                crd_line['account_id'] = int(provision_acc)
                crd_line['partner_id'] = customer.id if customer else False
                crd_tuple = (0, 0, crd_line)
                move_lines.append(crd_tuple)
                journal_id = self.env['ir.config_parameter'].sudo().get_param(
                    'kg_sarya_rebate.rebate_journal_id') or False
                if not journal_id:
                    raise UserError(_("Please configure Rebate journal from settings"))
                move = self.env['account.move'].create(
                    {'partner_id': customer.id, 'payment_reference': 'Rebate', 'rebate_master_id': rebate.id,
                     'ref': '%s -%s' % (rebate.name, inv.name), 'name': '/',
                     'journal_id': int(journal_id), 'enty_type': 'normal', 'sale_amount': sale_order_total,
                     'rebate_type': 'progressive', 'rebate_applied': rebate_applied, 'date': date.today(),
                     'invoice_date': date.today(), 'line_ids': move_lines,
                     'sale_order_id': sale_order.id,
                     'sale_order_customer_id': child_partner.id, })
                move.action_post()
                # this is the base table used for the previous rebate calculation
                self.env['prg.rebate.realtime'].create(
                    {'child_partner': child_partner.id if child_partner else False, 'move_id': move.id,
                     'slab_reach': slab_reach, 'rebate_amount': total, 'date': date.today(),
                     'sale_order': sale_order.id, 'rebate_id': rebate.id, 'partner_id': customer.id,
                     'current_sale_amount': sale_order_total, 'total_sale': amount, 'rebate_applied': rebate_applied,
                     'rebate_updated': rebate_applied})


class StockPickingInh(models.Model):
    _inherit = "stock.picking"

    invoice_status = fields.Integer(default=0)
    confirm_status = fields.Boolean(string="Verified", default=False)
    payment_term_id = fields.Many2one(
        'account.payment.term', string='Payment Terms', check_company=True,  # Unrequired company
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", )
    invoice_id = fields.Many2one('account.move')

    def unreserve_quantity(self):

        quants = self.env['stock.quant'].sudo().search([])

        move_line_ids = []
        move_line_to_recompute_ids = []

        logging = ''

        for quant in quants:

            move_lines = self.env['stock.move.line'].search([
                ('product_id', '=', quant.product_id.id),
                ('location_id', '=', quant.location_id.id),
                ('lot_id', '=', quant.lot_id.id),
                ('package_id', '=', quant.package_id.id),
                ('owner_id', '=', quant.owner_id.id),
                ('product_qty', '!=', 0),
            ])

            move_line_ids += move_lines.ids
            reserved_on_move_lines = sum(move_lines.mapped('product_qty'))
            move_line_str = str.join(', ', [str(move_line_id) for move_line_id in move_lines.ids])

            if quant.location_id.should_bypass_reservation():
                # If a quant is in a location that should bypass the reservation, its `reserved_quantity` field
                # should be 0.
                if quant.reserved_quantity != 0:
                    logging += "Problematic quant found: %s (quantity: %s, reserved_quantity: %s)\n" % (
                        quant.id, quant.quantity, quant.reserved_quantity)
                    logging += "its `reserved_quantity` field is not 0 while its location should bypass the reservation\n"
                    if move_lines:
                        logging += "These move lines are reserved on it: %s (sum of the reservation: %s)\n" % (
                            move_line_str, reserved_on_move_lines)
                    else:
                        logging += "no move lines are reserved on it, you can safely reset its `reserved_quantity` to 0\n"
                    logging += '******************\n'
                    quant.write({'reserved_quantity': 0})
            else:
                # If a quant is in a reservable location, its `reserved_quantity` should be exactly the sum
                # of the `product_qty` of all the partially_available / assigned move lines with the same
                # characteristics.

                if quant.reserved_quantity == 0:
                    if move_lines:
                        logging += "Problematic quant found: %s (quantity: %s, reserved_quantity: %s)\n" % (
                            quant.id, quant.quantity, quant.reserved_quantity)
                        logging += "its `reserved_quantity` field is 0 while these move lines are reserved on it: %s (sum of the reservation: %s)\n" % (
                            move_line_str, reserved_on_move_lines)
                        logging += '******************\n'
                        move_lines.with_context(bypass_reservation_update=True).sudo().write({'product_uom_qty': 0})
                        move_line_to_recompute_ids += move_lines.ids
                elif quant.reserved_quantity < 0:
                    logging += "Problematic quant found: %s (quantity: %s, reserved_quantity: %s)\n" % (
                        quant.id, quant.quantity, quant.reserved_quantity)
                    logging += "its `reserved_quantity` field is negative while it should not happen\n"
                    quant.write({'reserved_quantity': 0})
                    if move_lines:
                        logging += "These move lines are reserved on it: %s (sum of the reservation: %s)\n" % (
                            move_line_str, reserved_on_move_lines)
                        move_lines.with_context(bypass_reservation_update=True).sudo().write({'product_uom_qty': 0})
                        move_line_to_recompute_ids += move_lines.ids
                    logging += '******************\n'
                else:
                    if reserved_on_move_lines != quant.reserved_quantity:
                        logging += "Problematic quant found: %s (quantity: %s, reserved_quantity: %s)\n" % (
                            quant.id, quant.quantity, quant.reserved_quantity)
                        logging += "its `reserved_quantity` does not reflect the move lines reservation\n"
                        logging += "These move lines are reserved on it: %s (sum of the reservation: %s)\n" % (
                            move_line_str, reserved_on_move_lines)
                        logging += '******************\n'
                        move_lines.with_context(bypass_reservation_update=True).sudo().write({'product_uom_qty': 0})
                        move_line_to_recompute_ids += move_lines.ids
                        quant.write({'reserved_quantity': 0})
                    else:
                        if any(move_line.product_qty < 0 for move_line in
                               move_lines):
                            logging += "Problematic quant found: %s (quantity: %s, reserved_quantity: %s)\n" % (
                                quant.id, quant.quantity, quant.reserved_quantity)
                            logging += "its `reserved_quantity` correctly reflects the move lines reservation but some are negatives\n"
                            logging += "These move lines are reserved on it: %s (sum of the reservation: %s)\n" % (
                                move_line_str, reserved_on_move_lines)
                            logging += '******************\n'
                            move_lines.with_context(bypass_reservation_update=True).sudo().write({'product_uom_qty': 0})
                            move_line_to_recompute_ids += move_lines.ids
                            quant.write({'reserved_quantity': 0})

        move_lines = self.env['stock.move.line'].search([('product_id.type', '=',
                                                          'product'), ('product_qty', '!=', 0), ('id', 'not in',
                                                                                                 move_line_ids)])

        move_lines_to_unreserve = []

        for move_line in move_lines:
            if not move_line.location_id.should_bypass_reservation():
                logging += "Problematic move line found: %s (reserved_quantity: %s)\n" % (
                    move_line.id, move_line.product_qty)
                logging += "There is no exiting quants despite its `reserved_quantity`\n"
                logging += '******************\n'
                move_lines_to_unreserve.append(move_line.id)
                move_line_to_recompute_ids.append(move_line.id)

        if len(move_lines_to_unreserve) > 0:
            # self.env.cr.execute("""UPDATE stock_move_line SET product_uom_qty = 0, product_qty = 0 WHERE id in %s ;"""% (move_lines_to_unreserve), ))
            self.env.cr.execute(
                """UPDATE stock_move_line SET product_uom_qty = 0, product_qty = 0 WHERE id in(%s) ;""" % (
                    (move_lines_to_unreserve[0])))

        if logging:
            self.env['ir.logging'].sudo().create({
                'name': 'Unreserve stock.quant and stock.move.line',
                'type': 'server',
                'level': 'DEBUG',
                'dbname': self.env.cr.dbname,
                'message': logging,
                'func': '_update_reserved_quantity',
                'path': 'addons/stock/models/stock_quant.py',
                'line': '0',
            })

        if move_line_to_recompute_ids:
            self.env['stock.move.line'].browse(move_line_to_recompute_ids).move_id._recompute_state()

    # def button_confirm(self):
    #     if self.sale_id and self.picking_type_id.code == 'outgoing':
    #         for move in self.move_ids_without_package:
    #             if move.show_details_visible == True:
    #                 for line in move.move_line_ids:
    #                     if line.qty_done == 0 and move.pkg_done == 0:
    #                         line.qty_done = 0
    #                     elif line.qty_done == 0:
    #                         line.qty_done = line.product_uom_qty
    #                     else:
    #                         line.qty_done = line.qty_done
    #
    #                 if len(move.move_line_ids) == 0 and move.pkg_done > 0:
    #                     qty_done = move.pkg_done * move.product_packaging_id.qty
    #                     self.env['stock.move.line'].create(
    #                         {'product_uom_qty': qty_done, 'location_dest_id': move.location_dest_id.id,
    #                          'location_id': move.location_id.id, 'product_uom_id': move.product_uom.id,
    #                          'move_id': move.id, 'picking_id': move.picking_id.id, 'product_id': move.product_id.id,
    #                          'qty_done': qty_done})
    #
    #                     # move.quantity_done = move.pkg_done
    #
    #             else:
    #                 packaging_uom = move.product_packaging_id.product_uom_id
    #                 packaging_uom_qty = move.product_uom._compute_quantity(move.pkg_done, packaging_uom)
    #                 move.quantity_done = packaging_uom_qty * move.product_packaging_id.qty
    #             # for line in move.move_line_ids:
    #             #     lot_id = self.env['stock.production.lot'].create({'name':'1234','company_id':self.env.company.id,'product_id':line.product_id.id})
    #             #     line.write({'lot_id':lot_id.id})
    #
    #         self.confirm_status = True


    #This function called validating picking
    #This is check stock is available in the location from where items are delivering
    def check_lot_location(self):
        products = []
        product_name = ''
        if self.picking_type_id.code != 'incoming':
            for move in self.move_ids_without_package:
                for move_lines in move.move_line_ids:
                    if move_lines and not move_lines.lot_id:
                        raise ValidationError(
                            _("888 You need to supply a Lot/Serial number for product's %s.") % move_lines.product_id.name)
                    if move_lines.qty_done > 0 or move_lines.product_uom_qty > 0:
                        #Cha change Check available qty at the time of confirmation
                        available_quantity = 0
                        stock_on_hand = 0
                        quants = self.env['stock.quant'].search([('product_id', '=', move_lines.product_id.id),
                                                                 ('lot_id', 'in', move_lines.lot_id.ids),
                                                                 #('quantity', '>=', move_lines.qty_done),
                                                                 ('location_id', '=', move_lines.location_id.id),
                                                                 ('company_id', '=', move.company_id.id),
                                                                 ('location_id.usage', 'in', ('internal', 'transit'))])
                        for e_quant in quants:
                            if e_quant.available_quantity > 0.01:
                                available_quantity = available_quantity + e_quant.available_quantity
                            if e_quant.quantity > 0.01:
                                stock_on_hand = stock_on_hand + e_quant.quantity

                        qty_done = round(move_lines.qty_done, 4)
                        stock_on_hand = round(stock_on_hand, 4)
                        product_uom_qty = round(move_lines.product_uom_qty, 4)
                        if move_lines.qty_done > 0:
                            # Checking stock if stock quantity entered manually
                            # Needed to manually entered stock already available on stock on hand
                            if qty_done > stock_on_hand:
                                waring_msg = "Item: %s, Location: %s, Batch: %s, Picking %s, : Stock Required: %s, Stock On Hand only %s" % (move_lines.product_id.name,
                                            move_lines.location_id.name, move_lines.lot_id.name, move.picking_id.name, str(qty_done), str(stock_on_hand))
                                products.append(waring_msg)
                        elif move_lines.product_uom_qty > 0:
                            #Checking reserved stock is available in stock
                            if product_uom_qty > stock_on_hand:
                                waring_msg = "Item: %s, Location: %s, Batch: %s, Picking %s, : Stock Required: %s, Stock On Hand only %s" % (
                                                move_lines.product_id.name, move_lines.location_id.name,
                                                move_lines.lot_id.name, move.picking_id.name, str(product_uom_qty), str(stock_on_hand))
                                products.append(waring_msg)

                        #if (available_quantity + move_lines.product_uom_qty) <  round(move_lines.qty_done, 4):
                        #    products.append(move_lines.product_id.name)
                        #End
            if products:
                product_name = "\n\n".join(products)
                raise ValidationError(
                    _("Not enough stock!!\n\nPlease read below information and check weather the stock is available on below locations on the Batch Number mentioned \n\n %s") % product_name)


    def button_validate(self):
        method_start_time = datetime.now()
        self.invoice_status = 1
        #self.delivery_status = "out_for_delivery"
        #self.button_confirm()
        #self.check_lot_location()
        # self.unreserve_quantity()
        res = super(StockPickingInh, self).button_validate()
        for rec in self:
            if rec.sale_id and rec.picking_type_id.code == 'outgoing':# and rec.confirm_status:
                if res == True:
                    if not rec.partner_id.do_not_automate_invoice:
                        rec.create_invoice_on_delivery()
            _logger.info("Button Validate for %s : Method duration = %d seconds" % ((rec.name,
                                                                                     (
                                                                                             datetime.now() - method_start_time).total_seconds())))
        return res

    def view_invoice(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        invoice = self.env['account.move'].search([('id', '=', self.invoice_id.id)])
        if len(invoice) > 0:
            action['domain'] = [('id', 'in', invoice.ids)]
        return action

    def action_create_invoice(self):
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_view_sale_advance_payment_inv")
        so_ids = self.sale_id
        action['context'] = {
            'active_id': so_ids.id,
            'active_ids': so_ids.ids
        }
        return action


class SaleOrderInh(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        """passing picking id to delivery order"""
        res = super(SaleOrderInh, self).action_confirm()
        picking = self.env['stock.picking'].search([('sale_id', '=', self.id)])
        for pick in picking:
            pick.payment_term_id = self.payment_term_id
            pick.location_id = self.picking_type_id.default_location_src_id
            for move in pick.move_line_ids_without_package:
                move.location_id = self.picking_type_id.default_location_src_id.id
        return res


class StockMoveInh(models.Model):
    _inherit = "stock.move"

    def _should_bypass_reservation(self, forced_location=False):
        """overrided to solve the error"""
        if len(self) > 0:
            self.ensure_one()
            location = forced_location or self.location_id
            return location.should_bypass_reservation() or self.product_id.type != 'product'
