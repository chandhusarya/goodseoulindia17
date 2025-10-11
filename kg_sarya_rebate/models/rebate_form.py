# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools import float_repr, format_datetime
from datetime import date
from odoo.exceptions import ValidationError,UserError
from datetime import date
import time


class RebateForm(models.Model):
    _name = "customer.rebate"
    _description = "Rebate Form"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'rebate'

    def _get_default_year(self):
        return date.today().year

    rebate = fields.Many2one('rebate.master')
    date_start = fields.Date('Start Date', help="Starting for the rebatelist item validation",
                             default=time.strftime('%Y-01-01'))
    date_end = fields.Date('End Date', help="Ending for the rebatelist item validation", default=fields.Datetime.now)
    customer_line = fields.One2many('customer.rebate.line', 'line_customer')
    credit_count = fields.Integer(compute='_credit_count')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    rebate_status = fields.Boolean(default=False)
    year = fields.Integer(default=_get_default_year)

    # @api.onchange('rebate')
    # def rebate_period(self):
    #   if self.rebate:
    #       self.date_start = self.rebate.date_start
    #       self.date_end = self.rebate.date_end

    def load_customers(self):
        """Loading customer with rebate value"""
        company_id = self.env.company
        pricelist_item = self.env['product.pricelist'].search([('rebate_ids', '=', self.rebate.ids)])
        product_list = pricelist_item.mapped('item_ids.product_tmpl_id.product_variant_ids')
        customer_ids = pricelist_item.mapped('customer_ids')
        products = tuple(product_list)
        cr = self._cr
        for customer in customer_ids:
            ledger_list = []
            total = 0.0
            amount = 0.0
            rebate_applied = 0.0
            price_list = pricelist_item.ids
            cr.execute(
                "select sum(sl.qty_delivered) as qty,sl.price_unit,sl.product_id from sale_order s left join sale_order_line sl on s.id= sl.order_id where s.date_order<='" + str(
                    self.date_end) + "' and s.date_order>= '" + str(self.date_start) + "' and sl.product_id in" + str(
                    products) +
                "and s.partner_id = %s and s.pricelist_id in %s and sl.qty_delivered >0"
                                                 "group by sl.product_id,sl.price_unit", (customer.id, tuple(price_list)))
            product_dtls = cr.dictfetchall()
            # finding total sales value of product which can apply rebate
            for prd in product_dtls:
                amount = amount + (prd['qty'] * prd['price_unit'])
            prgrsv_items = self.env['rebate.progressive.item'].search(
                [('rebate_id', '=', self.rebate.id), ('slab_type', '=', 'percentage')], order='percentage desc')
            if len(prgrsv_items) > 0:
                prg_acc = prgrsv_items[0].account_id.id
                # finding percentage of previous sales value based on each slab and checking if it is greater than amount
                total = 0
                for prg in prgrsv_items:
                    percent_amt = (prg.percentage / 100) * self.rebate.prevous_amount
                    if amount > (self.rebate.prevous_amount + percent_amt):
                        ledger_list.append(
                            {'account_id': prg.account_id.id, 'amount': (prg.rebate_percentage / 100) * amount})
                        rebate_acc = prg.account_id.id
                        total = total + ((prg.rebate_percentage / 100) * amount)
                        rebate_applied = prg.rebate_percentage
                        break
                # checking if rebate percentage not achived yet then apply large rebate
                if total == 0:
                    prgrsv_large = self.env['rebate.progressive.item'].search(
                        [('rebate_id', '=', self.rebate.id), ('slab_type', '=', 'percentage')], order='percentage desc',
                        limit=1)
                    for el in prgrsv_large:
                        rebate_applied = el.rebate_percentage
                        total = (el.rebate_percentage / 100) * amount
                else:
                    prv_entry = self.env['customer.rebate'].search(
                        [('rebate', '=', self.rebate.id), ('year', '=', date.today().year), ('id', '!=', self.id)])
                    for entr in prv_entry:
                        rebate_line = self.env['customer.rebate.line'].search(
                            [('line_customer', '=', entr.id), ('customer_id', '=', customer.id)], limit=1)
                        if len(rebate_line) > 0:
                            if rebate_line.rebate_applied > rebate_applied:
                                reverse_rebate = rebate_line.rebate_applied - rebate_applied
                                reverse_amount = (reverse_rebate / 100) * amount
                                move_lines = []
                                a = {}
                                a['credit'] = total
                                a['partner_id'] = company_id.partner_id.id if company_id.partner_id.id else False
                                a['account_id'] = prg_acc
                                c = (0, 0, a)
                                move_lines.append(c)
                                b = {}
                                b['debit'] = total
                                b['account_id'] = customer.property_account_receivable_id.id
                                b['partner_id'] = customer.id if customer else False
                                d = (0, 0, b)
                                move_lines.append(d)
                                journal_id = self.env['ir.config_parameter'].sudo().get_param('kg_sarya_rebate.rebate_journal_id') or False
                                if not journal_id:
                                    raise UserError(_("Please configure Rebate journal from settings"))
                                move = self.env['account.move'].create(
                                    {'payment_reference': 'Rebate', 'rebate_id': self.id, 'ref': self.rebate.name,
                                     'name': '/', 'journal_id': int(journal_id), 'date': date.today(),
                                     'line_ids': move_lines})
                            elif rebate_line.rebate_applied < rebate_applied:
                                reverse_rebate = rebate_applied - rebate_line.rebate_applied
                                reverse_amount = (reverse_rebate / 100) * amount
                                move_lines = []
                                a = {}
                                a['debit'] = total
                                a['partner_id'] = company_id.partner_id.id if company_id.partner_id.id else False
                                a['account_id'] = prg_acc
                                c = (0, 0, a)
                                move_lines.append(c)
                                b = {}
                                b['credit'] = total
                                b['account_id'] = customer.property_account_receivable_id.id
                                b['partner_id'] = customer.id if customer else False
                                d = (0, 0, b)
                                move_lines.append(d)
                                journal_id = self.env['ir.config_parameter'].sudo().get_param('kg_sarya_rebate.rebate_journal_id') or False
                                if not journal_id:
                                    raise UserError(_("Please configure Rebate journal from settings"))
                                move = self.env['account.move'].create(
                                    {'payment_reference': 'Rebate','rebate_id': self.id, 'ref': self.rebate.name,
                                     'name': '/', 'journal_id': int(journal_id), 'date': date.today(),
                                     'line_ids': move_lines})
            prgrsv_items = self.env['rebate.progressive.item'].search(
                [('rebate_id', '=', self.rebate.id), ('slab_type', '=', 'fixed')], order='slab_vale desc')
            if len(prgrsv_items) > 0:
                prg_acc = prgrsv_items[0].account_id.id
                total = 0
                for prg in prgrsv_items:
                    if amount >= prg.slab_vale:
                        ledger_list.append(
                            {'account_id': prg.account_id.id, 'amount': (prg.rebate_percentage / 100) * amount})
                        rebate_acc = prg.account_id.id
                        total = total + ((prg.rebate_percentage / 100) * amount)
                        rebate_applied = prg.rebate_percentage
                        break
                if total == 0:
                    prgrsv_large = self.env['rebate.progressive.item'].search(
                        [('rebate_id', '=', self.rebate.id), ('slab_type', '=', 'fixed')], order='percentage desc',
                        limit=1)
                    for el in prgrsv_large:
                        rebate_applied = el.rebate_percentage
                        total = (el.rebate_percentage / 100) * amount
                else:
                    prv_entry = self.env['customer.rebate'].search(
                        [('rebate', '=', self.rebate.id), ('year', '=', date.today().year), ('id', '!=', self.id)])
                    for entr in prv_entry:
                        rebate_line = self.env['customer.rebate.line'].search(
                            [('line_customer', '=', entr.id), ('customer_id', '=', customer.id)], limit=1)
                        if len(rebate_line) > 0:
                            if rebate_line.rebate_applied > rebate_applied:
                                reverse_rebate = rebate_line.rebate_applied - rebate_applied
                                reverse_amount = (reverse_rebate / 100) * amount
                                move_lines = []
                                a = {}
                                a['credit'] = total
                                a['partner_id'] = company_id.partner_id.id if company_id.partner_id.id else False
                                a['account_id'] = prg_acc
                                c = (0, 0, a)
                                move_lines.append(c)
                                b = {}
                                b['debit'] = total
                                b['account_id'] = customer.property_account_receivable_id.id
                                b['partner_id'] = customer.id if customer else False
                                d = (0, 0, b)
                                move_lines.append(d)
                                journal_id = self.env['ir.config_parameter'].sudo().get_param('kg_sarya_rebate.rebate_journal_id') or False
                                if not journal_id:
                                    raise UserError(_("Please configure Rebate journal from settings"))
                                move = self.env['account.move'].create(
                                    {'payment_reference': 'Rebate', 'rebate_id': self.id, 'ref': self.rebate.name,
                                     'name': '/', 'journal_id': int(journal_id), 'date': date.today(),
                                     'line_ids': move_lines})
                            elif rebate_line.rebate_applied < rebate_applied:
                                reverse_rebate = rebate_applied - rebate_line.rebate_applied
                                reverse_amount = (reverse_rebate / 100) * amount
                                move_lines = []
                                a = {}
                                a['debit'] = total
                                a['partner_id'] = company_id.partner_id.id if company_id.partner_id.id else False
                                a['account_id'] = prg_acc
                                c = (0, 0, a)
                                move_lines.append(c)
                                b = {}
                                b['credit'] = total
                                b['account_id'] = customer.property_account_receivable_id.id
                                b['partner_id'] = customer.id if customer else False
                                d = (0, 0, b)
                                move_lines.append(d)
                                journal_id = self.env['ir.config_parameter'].sudo().get_param('kg_sarya_rebate.rebate_journal_id') or False
                                if not journal_id:
                                    raise UserError(_("Please configure Rebate journal from settings"))
                                move = self.env['account.move'].create(
                                    {'payment_reference': 'Rebate', 'rebate_id': self.id, 'ref': self.rebate.name,
                                     'name': '/', 'journal_id': int(journal_id), 'date': date.today(),
                                     'line_ids': move_lines})
            if total > 0:
                cust_rebate_line = self.env['customer.rebate.line'].create(
                    {'customer_id': customer.id, 'line_customer': self.id, 'amount': total, 'sales_value': amount,
                     'rebate_applied': rebate_applied})
            if total > 0:
                move_lines = []
                # a = {}
                # for el in ledger_list:
                a = {}
                a['debit'] = total
                a['partner_id'] = company_id.partner_id.id if company_id.partner_id.id else False
                a['account_id'] = prg_acc
                c = (0, 0, a)
                move_lines.append(c)
                b = {}
                b['credit'] = total
                b['account_id'] = customer.property_account_receivable_id.id
                b['partner_id'] = customer.id if customer else False
                d = (0, 0, b)
                move_lines.append(d)
                journal_id = self.env['ir.config_parameter'].sudo().get_param('kg_sarya_rebate.rebate_journal_id') or False
                if not journal_id:
                    raise UserError(_("Please configure Rebate journal from settings"))
                move = self.env['account.move'].create(
                    {'payment_reference': 'Rebate',
                     'rebate_id': self.id,
                     'ref': self.rebate.name,
                     'name': '/',
                     'journal_id': int(journal_id),
                     'date': date.today(),
                     'rebate_type': 'progressive',
                     'line_ids': move_lines})
            # move.action_post()
            # print(move)
            # print(errr)
        # print("product_dtls--->%s",product_dtls)
        self.rebate_status = True

    def rebate_calc_month_end(self):
        """Loading customer with rebate value by scheduler"""
        rebates = self.env['rebate.master'].search(
            [('date_start', '<=', date.today()), ('date_end', '>=', date.today())])
        company_id = self.env.company
        for rebate in rebates:
            cur_rebate = self.env['customer.rebate'].create(
                {'rebate': rebate.id, 'date_start': time.strftime('%Y-01-01'), 'date_end': date.today(),
                 'rebate_status': True, 'year': date.today().year})
            pricelist_item = self.env['product.pricelist'].search([('rebate_ids', '=', rebate.id)])
            product_list = []
            cust_list = []
            for prlist in pricelist_item:
                for item in prlist.item_ids:
                    product = self.env['product.product'].search([('product_tmpl_id', '=', item.product_tmpl_id.id)])
                    for prd in product:
                        product_list.append(prd.id)
                for cust in prlist.customer_ids:
                    cust_list.append(cust)
            products = tuple(product_list)
            cr = self._cr
            for customer in cust_list:
                ledger_list = []
                total = 0.0
                amount = 0.0
                rebate_applied = 0.0
                cr.execute(
                    "select sum(sl.qty_delivered) as qty,sl.price_unit,sl.product_id from sale_order s left join sale_order_line sl on s.id= sl.order_id where s.date_order<='" + str(
                        date.today()) + "' and s.date_order>= '" + str(
                        time.strftime('%Y-01-01')) + "' and sl.product_id in" + str(products) +
                    "and s.partner_id = %s and s.pricelist_id in %s and sl.qty_delivered >0"
                                                     "group by sl.product_id,sl.price_unit", (customer.id, tuple(pricelist_item.ids)))
                product_dtls = cr.dictfetchall()
                # finding total sales value of product which can apply rebate
                for prd in product_dtls:
                    amount = amount + (prd['qty'] * prd['price_unit'])
                prgrsv_items = self.env['rebate.progressive.item'].search(
                    [('rebate_id', '=', rebate.id), ('slab_type', '=', 'percentage')], order='percentage desc')
                if len(prgrsv_items) > 0:
                    prg_acc = prgrsv_items[0].account_id.id
                    # finding percentage of previous sales value based on each slab and checking if it is greater than amount
                    total = 0
                    for prg in prgrsv_items:
                        percent_amt = (prg.percentage / 100) * rebate.prevous_amount
                        if amount > (rebate.prevous_amount + percent_amt):
                            ledger_list.append(
                                {'account_id': prg.account_id.id, 'amount': (prg.rebate_percentage / 100) * amount})
                            rebate_acc = prg.account_id.id
                            total = total + ((prg.rebate_percentage / 100) * amount)
                            rebate_applied = prg.rebate_percentage
                            break
                    # checking if rebate percentage not achived yet then apply large rebate
                    if total == 0:
                        prgrsv_large = self.env['rebate.progressive.item'].search(
                            [('rebate_id', '=', rebate.id), ('slab_type', '=', 'percentage')], order='percentage desc',
                            limit=1)
                        for el in prgrsv_large:
                            rebate_applied = el.rebate_percentage
                            total = (el.rebate_percentage / 100) * amount
                    else:
                        prv_entry = self.env['customer.rebate'].search(
                            [('rebate', '=', rebate.id), ('year', '=', date.today().year), ('id', '!=', cur_rebate.id)])
                        for entr in prv_entry:
                            rebate_line = self.env['customer.rebate.line'].search(
                                [('line_customer', '=', entr.id), ('customer_id', '=', customer.id)], limit=1)
                            if len(rebate_line) > 0:
                                if rebate_line.rebate_applied > rebate_applied:
                                    reverse_rebate = rebate_line.rebate_applied - rebate_applied
                                    reverse_amount = (reverse_rebate / 100) * amount
                                    move_lines = []
                                    a = {}
                                    a['credit'] = total
                                    a['partner_id'] = company_id.partner_id.id if company_id.partner_id.id else False
                                    a['account_id'] = prg_acc
                                    c = (0, 0, a)
                                    move_lines.append(c)
                                    b = {}
                                    b['debit'] = total
                                    b['account_id'] = customer.property_account_receivable_id.id
                                    b['partner_id'] = customer.id if customer else False
                                    d = (0, 0, b)
                                    move_lines.append(d)
                                    journal = self.env['account.move'].with_context(
                                        default_move_type='out_invoice')._get_default_journal()
                                    move = self.env['account.move'].create(
                                        {'payment_reference': 'Rebate', 'rebate_id': cur_rebate.id, 'ref': rebate.name,
                                         'name': '/', 'journal_id': int(journal_id), 'date': date.today(),
                                         'line_ids': move_lines})
                                elif rebate_line.rebate_applied < rebate_applied:
                                    reverse_rebate = rebate_applied - rebate_line.rebate_applied
                                    reverse_amount = (reverse_rebate / 100) * amount
                                    move_lines = []
                                    a = {}
                                    a['debit'] = total
                                    a['partner_id'] = company_id.partner_id.id if company_id.partner_id.id else False
                                    a['account_id'] = prg_acc
                                    c = (0, 0, a)
                                    move_lines.append(c)
                                    b = {}
                                    b['credit'] = total
                                    b['account_id'] = customer.property_account_receivable_id.id
                                    b['partner_id'] = customer.id if customer else False
                                    d = (0, 0, b)
                                    move_lines.append(d)
                                    journal = self.env['account.move'].with_context(
                                        default_move_type='out_invoice')._get_default_journal()
                                    move = self.env['account.move'].create(
                                        {'payment_reference': 'Rebate', 'rebate_id': cur_rebate.id, 'ref': rebate.name,
                                         'name': '/', 'journal_id': int(journal_id), 'date': date.today(),
                                         'line_ids': move_lines})
                prgrsv_items = self.env['rebate.progressive.item'].search(
                    [('rebate_id', '=', rebate.id), ('slab_type', '=', 'fixed')], order='slab_vale desc')
                if len(prgrsv_items) > 0:
                    prg_acc = prgrsv_items[0].account_id.id
                    total = 0
                    for prg in prgrsv_items:
                        if amount >= prg.slab_vale:
                            ledger_list.append(
                                {'account_id': prg.account_id.id, 'amount': (prg.rebate_percentage / 100) * amount})
                            rebate_acc = prg.account_id.id
                            total = total + ((prg.rebate_percentage / 100) * amount)
                            rebate_applied = prg.rebate_percentage
                            break
                    if total == 0:
                        prgrsv_large = self.env['rebate.progressive.item'].search(
                            [('rebate_id', '=', rebate.id), ('slab_type', '=', 'fixed')], order='percentage desc',
                            limit=1)
                        for el in prgrsv_large:
                            rebate_applied = el.rebate_percentage
                            total = (el.rebate_percentage / 100) * amount
                    else:
                        prv_entry = self.env['customer.rebate'].search(
                            [('rebate', '=', rebate.id), ('year', '=', date.today().year), ('id', '!=', cur_rebate.id)])
                        for entr in prv_entry:
                            rebate_line = self.env['customer.rebate.line'].search(
                                [('line_customer', '=', entr.id), ('customer_id', '=', customer.id)], limit=1)
                            if len(rebate_line) > 0:
                                if rebate_line.rebate_applied > rebate_applied:
                                    reverse_rebate = rebate_line.rebate_applied - rebate_applied
                                    reverse_amount = (reverse_rebate / 100) * amount
                                    move_lines = []
                                    a = {}
                                    a['credit'] = total
                                    a['partner_id'] = company_id.partner_id.id if company_id.partner_id.id else False
                                    a['account_id'] = prg_acc
                                    c = (0, 0, a)
                                    move_lines.append(c)
                                    b = {}
                                    b['debit'] = total
                                    b['account_id'] = customer.property_account_receivable_id.id
                                    b['partner_id'] = customer.id if customer else False
                                    d = (0, 0, b)
                                    move_lines.append(d)
                                    journal_id = self.env['ir.config_parameter'].sudo().get_param('kg_sarya_rebate.rebate_journal_id') or False
                                    if not journal_id:
                                        raise UserError(_("Please configure Rebate journal from settings"))
                                    move = self.env['account.move'].create(
                                        {'payment_reference': 'Rebate', 'rebate_id': cur_rebate.id, 'ref': rebate.name,
                                         'name': '/', 'journal_id': int(journal_id), 'date': date.today(),
                                         'line_ids': move_lines})
                                elif rebate_line.rebate_applied < rebate_applied:
                                    reverse_rebate = rebate_applied - rebate_line.rebate_applied
                                    reverse_amount = (reverse_rebate / 100) * amount
                                    move_lines = []
                                    a = {}
                                    a['debit'] = total
                                    a['partner_id'] = company_id.partner_id.id if company_id.partner_id.id else False
                                    a['account_id'] = prg_acc
                                    c = (0, 0, a)
                                    move_lines.append(c)
                                    b = {}
                                    b['credit'] = total
                                    b['account_id'] = customer.property_account_receivable_id.id
                                    b['partner_id'] = customer.id if customer else False
                                    d = (0, 0, b)
                                    move_lines.append(d)
                                    journal_id = self.env['ir.config_parameter'].sudo().get_param('kg_sarya_rebate.rebate_journal_id') or False
                                    if not journal_id:
                                        raise UserError(_("Please configure Rebate journal from settings"))
                                    move = self.env['account.move'].create(
                                        {'payment_reference': 'Rebate', 'rebate_id': cur_rebate.id, 'ref': rebate.name,
                                         'name': '/', 'journal_id': int(journal_id), 'date': date.today(),
                                         'line_ids': move_lines})
                if total > 0:
                    cust_rebate_line = self.env['customer.rebate.line'].create(
                        {'customer_id': customer.id, 'line_customer': cur_rebate.id, 'amount': total,
                         'sales_value': amount, 'rebate_applied': rebate_applied})
                if total > 0:
                    move_lines = []
                    # a = {}
                    # for el in ledger_list:
                    a = {}
                    a['debit'] = total
                    a['partner_id'] = company_id.partner_id.id if company_id.partner_id.id else False
                    a['account_id'] = prg_acc
                    c = (0, 0, a)
                    move_lines.append(c)
                    b = {}
                    b['credit'] = total
                    b['account_id'] = customer.property_account_receivable_id.id
                    b['partner_id'] = customer.id if customer else False
                    d = (0, 0, b)
                    move_lines.append(d)
                    journal_id = self.env['ir.config_parameter'].sudo().get_param('kg_sarya_rebate.rebate_journal_id') or False
                    if not journal_id:
                        raise UserError(_("Please configure Rebate journal from settings"))
                    move = self.env['account.move'].create(
                        {'payment_reference': 'Rebate', 'rebate_id': cur_rebate.id, 'ref': rebate.name, 'name': '/',
                         'journal_id': int(journal_id), 'date': date.today(), 'line_ids': move_lines})
                # move.action_post()
                # print(move)
                # print(errr)
            # print("product_dtls--->%s",product_dtls)
            self.rebate_status = True

    def _credit_count(self):
        for each in self:
            document_ids = self.env['account.move'].search([('rebate_id', '=', each.id)])
            each.credit_count = len(document_ids)

    def rebate_creditnote_view(self):
        self.ensure_one()
        domain = [
            ('rebate_id', '=', self.id)]
        return {
            'name': _('Credit Notes'),
            'domain': domain,
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
        }


class RebateCustomer(models.Model):
    _name = "customer.rebate.line"
    _description = "List of Customer for rebate"

    customer_id = fields.Many2one('res.partner')
    line_customer = fields.Many2one('customer.rebate', ondelete='cascade')
    rebate_line = fields.One2many('rebate.line', 'rebate_line')
    amount = fields.Float()
    sales_value = fields.Float()
    rebate_applied = fields.Float()
    state = fields.Integer(default=0)

    def get_line_vals(self, line_vals):
        return {
            'invoice_line_ids': [(0, 0, line_vals)]
        }

    def create_credit_note(self):
        """Creating Credit note entry"""
        ac_move = self.env['account.move'].create({
            'partner_id': self.customer_id.id,
            'move_type': 'out_refund',
            'payment_reference': 'Rebate',
            'invoice_date': date.today(),
            'rebate_id': self.line_customer.id,
        })
        for line in self.rebate_line:
            account = self.env['account.account'].search([('name', '=', 'Sales Expenses')]).id
            line_vals = {
                'move_id': ac_move.id,
                'product_id': line.product_id.id,
                'name': line.product_id.product_tmpl_id.name,
                'price_unit': line.total_amount,
                'account_id': account,
                'price_total': line.total_amount,
                'quantity': 1,
                'rebate_line_id': line.id,
                'rebate_entry': True,
                'rebate_date_end': self.line_customer.date_end,
            }
            move_vals = self.get_line_vals(line_vals)
            ac_move.write(move_vals)
            ac_move.action_post()

        self.state = 1


class RebateCustomer(models.Model):
    _name = "rebate.line"
    _description = "List of Rebate details for customer"

    rebate_line = fields.Many2one('customer.rebate.line')
    product_id = fields.Many2one('product.product')
    description = fields.Char()
    prevous_amount = fields.Float()
    prevous_rebate = fields.Float()
    prevous_percent = fields.Float()
    current_amount = fields.Float()
    current_rebate = fields.Float()
    current_percent = fields.Float()
    total_amount = fields.Float()
    total_rebate = fields.Float()
    customer_id = fields.Many2one('res.partner')


class AccountMoveLineRebate(models.Model):
    _inherit = "account.move.line"

    rebate_line_id = fields.Many2one('rebate.line')
    rebate_entry = fields.Boolean(default=False)
    rebate_date_end = fields.Date(help="Last Rebate Date")


class AccountMoveRebate(models.Model):
    _inherit = "account.move"

    rebate_id = fields.Many2one('customer.rebate', string="Customer Rebate")

# class PartnerInh(models.Model):
#     _inherit = "res.partner"
#     _description = "Storing nect slab"
#
#     next_slab = fields.Many2one('rebate.progressive.item', string="Next Slab")