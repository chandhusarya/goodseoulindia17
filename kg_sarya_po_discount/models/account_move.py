# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_compare, float_round
from datetime import date, timedelta, datetime
from odoo.tools import date_utils


class AccountMoveLineDiscInherit(models.Model):
    _inherit = "account.move.line"

    discount_1 = fields.Float(string='Disc 1')
    discount_2 = fields.Float(string='Disc 2')
    move_type = fields.Selection(
        related="move_id.move_type",
        string="Type",
        store=True
    )


class AccountMoveDiscInherit(models.Model):
    _inherit = "account.move"

    po_discount_entry_id = fields.Many2one('account.move', string="Purchase Discount Journal")

    def action_post(self):
        # Create discount entry while posting purchase bills
        res = super(AccountMoveDiscInherit, self).action_post()
        for move in self:
            if move.journal_id.type == 'purchase' and not move.po_discount_entry_id:
                if move.move_type == 'in_refund':
                    pass
                    # move.apply_po_discount_reversal()
                else:
                    move.apply_po_discount()
                move.po_discount_entry_id.action_post()
        return res

    def button_draft(self):
        # unlink all related rebate items to avoid duplicate records. Then updates related rebate entries.
        res = super(AccountMoveDiscInherit, self).button_draft()
        now = datetime.now()
        for move in self:
            if move.po_discount_entry_id:
                move.po_discount_entry_id.button_draft()
                if move.po_discount_entry_id.ref:
                    ref = move.po_discount_entry_id.ref  + " reset bill on : " + now.strftime("%d/%m/%Y, %H:%M:%S")
                else:
                    ref = "Reset bill on : " + now.strftime("%d/%m/%Y, %H:%M:%S")
                move.po_discount_entry_id.ref = ref
                move.po_discount_entry_id.button_cancel()
                move.po_discount_entry_id = False

        return res

    def apply_po_discount_reversal(self):
        if self.po_discount_entry_id:
            return True

        move_obj = self.env['account.move'].with_context(default_move_type='in_invoice')
        currency = self.currency_id
        currency_inr = self.env['res.currency'].search([('name', '=', 'INR')])
        total_debit = 0
        actual_amount_d1 = 0
        actual_amount_d2 = 0
        journal_entry = []
        name = "purchase discount for "
        if self.invoice_origin:
            name = name + self.invoice_origin

        for lines in self.invoice_line_ids:
            for suppliers in lines.product_id.seller_ids:
                get_supplier = suppliers.filtered(lambda x: (x.name == suppliers.name))
                if get_supplier:
                    disc1 = get_supplier.discount_1
                    disc2 = get_supplier.discount_2
                    if disc1 > 0.00000000001:
                        disc1_amount = currency.round(lines.price_subtotal * disc1)
                        actual_amount_d1 = currency._convert(disc1_amount, currency_inr)
                        lines.discount_1 = disc1_amount
                        acc_discount1_id = self.company_id.acc_discount1_id
                        if not acc_discount1_id.exists():
                            raise ValidationError(
                                _('Discount Account For Purchase Order is empty, Add your account in Accounts configuration settings '))
                        else:
                            journal_entry1 = (0, 0, {
                                'account_id': acc_discount1_id.id,
                                'partner_id': self.partner_id.id,
                                'name': name + lines.product_id.name,
                                'debit': actual_amount_d1,
                                'discount_1': disc1,
                                'discount_2': disc2,
                            })
                            journal_entry.append(journal_entry1)
                            total_debit += actual_amount_d1

                    if disc2 > 0.00000000001:

                        disc2_amount = currency.round(lines.price_subtotal * disc2)
                        actual_amount_d2 = currency._convert(disc2_amount, currency_inr)
                        lines.discount_2 = disc2_amount
                        acc_discount2_id = self.company_id.acc_discount2_id
                        if not acc_discount2_id.exists():
                            raise ValidationError(
                                _('Discount Account For Purchase Order is empty, Add your account in Acounts configuration settings '))
                        else:
                            journal_entry2 = (0, 0, {
                                'account_id': acc_discount2_id.id,
                                'partner_id': self.partner_id.id,
                                'name': name + lines.product_id.name,
                                'debit': actual_amount_d2,
                                'discount_1': disc1,
                                'discount_2': disc2,
                            })
                            journal_entry.append(journal_entry2)
                            total_debit +=  actual_amount_d2

        if journal_entry:
            name = "Reversal of Discount for "
            if self.invoice_origin:
                name = name + self.invoice_origin
            journal_entry_diff = (0, 0, {
                'account_id': self.partner_id.property_account_payable_id.id,
                'partner_id': self.partner_id.id,
                'name': name,
                'credit': total_debit
            })
            journal_entry.append(journal_entry_diff)
            create_entry = move_obj.create({'ref': self.name,
                'partner_id': self.partner_id.id,
                'invoice_date': self.date,
                'line_ids': journal_entry})

            self.po_discount_entry_id = create_entry.id


    def apply_po_discount(self):
        if self.po_discount_entry_id:
            return True
        move_obj = self.env['account.move'].with_context(default_move_type='in_refund')
        currency = self.currency_id
        currency_inr = self.env['res.currency'].search([('name', '=', 'INR')])
        total_debit = 0
        actual_amount_d1 = 0
        actual_amount_d2 = 0
        journal_entry = []
        name = "purchase discount for "
        if self.invoice_origin:
            name = self.invoice_origin


        for lines in self.invoice_line_ids:
            for suppliers in lines.product_id.seller_ids:
                get_supplier = suppliers.filtered(lambda x: (x.partner_id == suppliers.partner_id))
                if get_supplier:
                    disc1 = get_supplier.discount_1
                    disc2 = get_supplier.discount_2
                    if disc1 > 0.00000000001:
                        disc1_amount = currency.round(lines.price_subtotal * disc1)
                        actual_amount_d1 = currency._convert(disc1_amount, currency_inr)
                        print('actual_amount_d1', actual_amount_d1)
                        lines.discount_1 = disc1_amount
                        acc_discount1_id = self.company_id.acc_discount1_id
                        if not acc_discount1_id.exists():
                            raise ValidationError(
                                _('Discount Account For Purchase Order is empty, Add your account in Acounts configuration settings '))
                        else:
                            journal_entry1 = (0, 0, {
                                'account_id': acc_discount1_id.id,
                                'partner_id': self.partner_id.id,
                                'name': name + lines.product_id.name,
                                'credit': actual_amount_d1,
                                'quantity': 1,
                                'price_unit': actual_amount_d1,
                                'discount_1': disc1,
                                'discount_2': disc2,
                            })
                            journal_entry.append(journal_entry1)
                            total_debit += actual_amount_d1

                    if disc2 > 0.00000000001:

                        disc2_amount = currency.round(lines.price_subtotal * disc2)
                        actual_amount_d2 = currency._convert(disc2_amount, currency_inr)
                        lines.discount_2 = disc2_amount
                        acc_discount2_id = self.company_id.acc_discount2_id
                        if not acc_discount2_id.exists():
                            raise ValidationError(
                                _('Discount Account For Purchase Order is empty, Add your account in Acounts configuration settings '))
                        else:
                            journal_entry2 = (0, 0, {
                                'account_id': acc_discount2_id.id,
                                'partner_id': self.partner_id.id,
                                'name': name + lines.product_id.name,
                                'credit': actual_amount_d2,
                                'quantity': 1,
                                'price_unit': actual_amount_d2,
                                'discount_1': disc1,
                                'discount_2': disc2,
                            })
                            journal_entry.append(journal_entry2)
                            total_debit +=  actual_amount_d2

        if journal_entry:
            name = "Partner discount for "
            if self.invoice_origin:
                name = name + self.invoice_origin
            journal_entry_diff = (0, 0, {
                'account_id': self.partner_id.property_account_payable_id.id,
                'partner_id': self.partner_id.id,
                'name': name,
                'quantity': 1,
                'price_unit': total_debit,
                'debit': total_debit
            })
            journal_entry.append(journal_entry_diff)
            print('Lines:', journal_entry)
            create_entry = move_obj.create({'ref': self.name,
                'partner_id': self.partner_id.id,
                'invoice_date': self.date,
                'line_ids': journal_entry})

            self.po_discount_entry_id = create_entry.id


    def action_view_purchase_discount(self):

        po_journal_view = {
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.po_discount_entry_id.id,
            # 'view_id': self.po_discount_entry_id.id
        }
        return po_journal_view
