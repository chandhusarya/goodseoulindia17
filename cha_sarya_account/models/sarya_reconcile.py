# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _, api, SUPERUSER_ID
from odoo import models, fields, api
from odoo.exceptions import UserError
from collections import OrderedDict

class SaryaReconcile(models.Model):
    _name = "sarya.reconcile"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char("Name")
    partner_id = fields.Many2many('res.partner', string='Customer/Vendor')
    verified_by = fields.Many2one('res.users', string='Verified By')
    verified_for_reconcile = fields.Boolean(string="Show Verified Only", default=True)
    state = fields.Selection([
        ('new', 'New'), ('closed', 'Closed')], "State", default='new')
    master_parent_id = fields.Many2one('master.parent', string="Master Parent")
    journal_items_invoices = fields.Many2many('account.move.line',
                                    'sarya_reconcile_journal_items_invoices',
                                    string='Journal Items')
    journal_items_rebate_entries = fields.Many2many('account.move.line',
                                    'sarya_reconcile_journal_items_rebate_entries',
                                    string='Journal Items')
    summary_line_ids = fields.One2many('sarya.reconcile.summary', 'reconcile_id')
    rebate_previous_reconciliation = fields.Many2many('sarya.reconcile',
                                              'sarya_reconcile_previous_reconciliation',
                                              "reconcile_id", "previous_id",
                                              string='Previous Reconciliation')


    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('journal.item.reconcile') or _('New')
        res = super(SaryaReconcile, self).create(vals)
        return res


    def load_rebates_only(self):

        context = self.env.context.copy()
        load_rebate_vals = {
            'reconcile_id': self.id
        }
        load_rebate = self.env['sarya.reconcile.load.rebate'].create(load_rebate_vals)
        view_id = self.env.ref('cha_sarya_account.sarya_reconcile_load_rebate_view').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Load Rebate'),
            'view_mode': 'form',
            'res_model': 'sarya.reconcile.load.rebate',
            'target': 'new',
            'res_id': load_rebate.id,
            'views': [[view_id, 'form']],
            'context': context,
        }


    def reload_rebates(self):
        # Finding Rebate Entry
        self.journal_items_rebate_entries = False
        rebate_search_condition = [('account_id.account_type', 'in', ('asset_receivable', 'liability_payable')),
                                   ('move_id.state', '=', 'posted')]
        journal_id = self.env['ir.config_parameter'].sudo().get_param('kg_sarya_rebate.rebate_journal_id', False)
        print("3>>>>>>>>>>>>>>>>>>>>>>>>>>")
        if not journal_id:
            raise UserError(_("You must configure journal for rebate in settings"))
        journal_id = int(journal_id)
        rebate_search_condition.append(('move_id.journal_id', '=', journal_id))
        list_rebate_move_line = []

        for mv in self.journal_items_invoices:
            rebate_move_line = self.env['account.move.line'].search([('move_id.journal_id', '=', journal_id),
                                                                     ('move_id.fixed_rebate_move_id', '=', mv.move_id.id),
                                                                     ('account_id.account_type', 'in', ('asset_receivable', 'liability_payable')),
                                                                     ('move_id.state', '=', 'posted')])

            if rebate_move_line:
                for reb in rebate_move_line:
                    list_rebate_move_line.append(reb.id)
            else:
                rebate_search_condition_invoice = rebate_search_condition.copy()
                rebate_search_condition_invoice.append(('move_id.ref', 'ilike', mv.move_id.name))
                rebate_move_line = self.env['account.move.line'].search(rebate_search_condition_invoice)
                if rebate_move_line:
                    for r_move_line in rebate_move_line:
                        r_move_ref = r_move_line.move_id.ref
                        s_r_move_ref = r_move_ref.split("-")
                        if len(s_r_move_ref) == 2:
                            s_r_move_ref = s_r_move_ref[1].strip()
                            if s_r_move_ref == mv.move_id.name:
                                list_rebate_move_line.append(r_move_line.id)

        #Loading rebate entries from previous statements if it is selected
        for rebate_previous_reconciliation in self.rebate_previous_reconciliation:
            for previous_rebate in rebate_previous_reconciliation.journal_items_rebate_entries:
                print("====>> ", previous_rebate.amount_residual)
                if previous_rebate.amount_residual != 0 and previous_rebate.id not in list_rebate_move_line:
                    list_rebate_move_line.append(previous_rebate.id)
        

        if list_rebate_move_line:
            self.journal_items_rebate_entries = list_rebate_move_line

    def load_entries(self):
        #Finding All invoices
        self.journal_items_invoices = False
        search_condition = [('account_id.account_type', 'in', ('asset_receivable', 'liability_payable')),
                            ('move_id.state', '=', 'posted'),('amount_residual','!=', 0)]
        if self.partner_id:
            search_condition.append(('partner_id', 'in', self.partner_id.ids))
        if self.master_parent_id:
            master_parent_partner_ids = self.env['res.partner'].search([
                ('master_parent_id', '=', self.master_parent_id.id)])
            if master_parent_partner_ids:
                search_condition.append(('partner_id', 'in', master_parent_partner_ids.ids))
        if self.verified_for_reconcile:
            search_condition.append(('move_id.verified_for_reconcile', '=', self.verified_for_reconcile))
        if self.verified_by:
            search_condition.append(('move_id.verified_for_reconcile_by', '=', self.verified_by.id))

        #filter_for_invoice
        journal_ids = self.env['account.journal'].search([
            ('type', 'in', ['sale', 'purchase'])])
        search_condition.append(('move_id.journal_id', 'in', journal_ids.ids))
        move_line = self.env['account.move.line'].search(search_condition)
        if move_line:
            self.journal_items_invoices = move_line.ids

        self.reload_rebates()
        self.update_summary()

    def update_summary(self):

        self.summary_line_ids.unlink()
        partner_wise = {}
        for inv in self.journal_items_invoices:
            key = (inv.partner_id.id, "Invoice")
            if key not in partner_wise:
                partner_wise[key] = {'amount' : inv.amount_residual}

            else:
                amount = inv.amount_residual
                partner_wise[key]['amount'] = partner_wise[key]['amount'] + amount

        for rebate in self.journal_items_rebate_entries:
            key = (rebate.partner_id.id, rebate.name)
            if key not in partner_wise:
                partner_wise[key] = {'amount': rebate.amount_residual}

            else:
                amount = rebate.amount_residual
                partner_wise[key]['amount'] = partner_wise[key]['amount'] + amount


        print("partner_wise ==>> ", partner_wise)

        partner_wise_data = {}
        for key in partner_wise:
            partner_id = key[0]
            description = key[1]
            amount = partner_wise[key]['amount']
            if partner_id not in partner_wise_data:
                partner_wise_data[partner_id] = {key : amount}
            else:
                partner_wise_data[partner_id][key] = amount

        data_to_sort = OrderedDict(sorted(partner_wise_data.items()))

        for partner_id in data_to_sort:
            total = 0
            for key in data_to_sort[partner_id]:
                amount = data_to_sort[partner_id][key]
                total = total + amount
                vals = {
                    'partner_id' : key[0],
                    'description': key[1],
                    'amount': amount,
                    'is_total' : False,
                    'reconcile_id' : self.id
                }
                self.env['sarya.reconcile.summary'].create(vals)
            vals = {
                'partner_id': partner_id,
                'description': "Total",
                'amount': total,
                'is_total': True,
                'reconcile_id': self.id
            }
            self.env['sarya.reconcile.summary'].create(vals)


    def close_reconcilation(self):
        for journal_items in self.journal_items_invoices:
           journal_items.move_id.verified_for_reconcile = False
        self.state = 'closed'


class SaryaReconcileSummary(models.Model):
    _name = "sarya.reconcile.summary"

    reconcile_id = fields.Many2one('sarya.reconcile', string='Reconcile')
    partner_id = fields.Many2one('res.partner', string='Customer/Vendor')
    payment_id = fields.Many2one('account.payment', string='Payment')
    description = fields.Char("Description")
    amount = fields.Float("Amount")
    is_total = fields.Boolean("Total")
    partial_reconcile_ids = fields.Many2many('account.partial.reconcile', string='Partial Reconcile')

    def reconcile_invoice_credit_notes(self):
        for mv in self.reconcile_id.journal_items_invoices:
            if mv.partner_id.id == self.partner_id.id:
                if mv.move_id.reversed_entry_id:
                    can_reconcile = False
                    list_rebate_move_line = []
                    list_rebate_move_line.append(mv.id)
                    for mv_counter in self.reconcile_id.journal_items_invoices:
                        if mv_counter.move_id.id == mv.move_id.reversed_entry_id.id:
                            list_rebate_move_line.append(mv_counter.id)
                            can_reconcile = True
                    if can_reconcile:
                        move_lines_to_reconcile = self.env['account.move.line'].browse(list_rebate_move_line)
                        move_lines_to_reconcile.reconcile()

    def reconcile_invoice_grv_rebates(self):
        for mv in self.reconcile_id.journal_items_invoices:
            if mv.partner_id.id == self.partner_id.id:
                list_rebate_move_line = []
                for r_move_line in self.reconcile_id.journal_items_rebate_entries:
                    r_move_ref = r_move_line.move_id.ref
                    s_r_move_ref = r_move_ref.split("-")
                    if len(s_r_move_ref) == 2:
                        s_r_move_ref = s_r_move_ref[1].strip()
                        if s_r_move_ref == mv.move_id.name:
                            list_rebate_move_line.append(r_move_line.id)
                if list_rebate_move_line:
                    list_rebate_move_line.append(mv.id)
                    move_lines_to_reconcile = self.env['account.move.line'].browse(list_rebate_move_line)
                    move_lines_to_reconcile.reconcile()

    def reconcile(self):
        journal_items_to_reconcile = []
        partner_id = self.partner_id.id
        for item in self.reconcile_id.journal_items_invoices:
            if item.partner_id.id == partner_id:
                if item.amount_residual != 0:
                    journal_items_to_reconcile.append(item.id)
        for item in self.reconcile_id.journal_items_rebate_entries:
            if item.partner_id.id == partner_id:
                if item.amount_residual != 0:
                    journal_items_to_reconcile.append(item.id)
        if self.payment_id and self.payment_id.state == 'posted':
            for move in self.payment_id.move_id:
                for item in move.line_ids:
                    if item.account_id.account_type in ('asset_receivable', 'liability_payable'):
                        if item.amount_residual != 0:
                            journal_items_to_reconcile.append(item.id)
        return {
            'type': 'ir.actions.client',
            'name': _('Reconcile'),
            'tag': 'manual_reconciliation_view',
            'binding_model_id': self.env['ir.model.data']._xmlid_to_res_id('account.model_account_move_line'),
            'binding_type': 'action',
            'binding_view_types': 'list',
            'context': {'active_ids': journal_items_to_reconcile, 'active_model': 'account.move.line'},
        }

    def create_payment(self):
        view_id = self.env.ref('account.view_account_payment_form').id
        context = {
            'default_partner_id' : self.partner_id.id,
            'default_amount': self.amount,
            'sarya_reconcile_summary' : self.id,
        }
        return {
            'name': 'Payment',
            'view_type': 'form',
            'view_mode': 'tree',
            'views': [(view_id, 'form')],
            'res_model': 'account.payment',
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }

    def partial_reconcile_window(self):
        context = self.env.context.copy()
        payment_id = False
        if self.payment_id and self.payment_id.state == 'posted':
            for move in self.payment_id.move_id:
                for item in move.line_ids:
                    if item.account_id.account_type in ('asset_receivable', 'liability_payable'):
                        if item.amount_residual != 0:
                            payment_id = item.id

        reconcile_partial_vals = {
            'partner_id': self.partner_id.id,
            'payment_id' : payment_id and payment_id or False}
        reconcile_partial = self.env['sarya.reconcile.partial'].create(reconcile_partial_vals)
        reconcile_partial._onchange_payment()

        for item in self.reconcile_id.journal_items_invoices:
            if item.partner_id.id == self.partner_id.id:
                if item.amount_residual != 0:
                    reconcile_partial_line_vals = {
                        'inv_date' : item.date,
                        'reconcile_partial_id': reconcile_partial.id,
                        'move_id': item.id,
                        'amount_residual' : item.amount_residual}
                    self.env['sarya.reconcile.partial.line'].create(reconcile_partial_line_vals)

        view_id = self.env.ref('cha_sarya_account.sarya_reconcile_partial_view').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Partial Allocation'),
            'view_mode': 'form',
            'res_model': 'sarya.reconcile.partial',
            'target': 'new',
            'res_id': reconcile_partial.id,
            'views': [[view_id, 'form']],
            'context': context,
        }

    def partial_reconcile(self, debit_lines, credit_line, partial_amount):
        reconciliation_partials = self._prepare_reconciliation_partials(debit_lines, credit_line, partial_amount)
        partials = self.env['account.partial.reconcile'].create(reconciliation_partials)
        self.write({'partial_reconcile_ids': [(6, 0, partials.ids)]})

    def _prepare_reconciliation_partials(self, debit_lines, credit_line, partial_amount):
        partials_vals_list = []
        for debit_line in debit_lines:
            partials_vals_list.append({
                'amount': partial_amount,
                'debit_amount_currency': partial_amount,
                'credit_amount_currency': partial_amount,
                'debit_move_id': debit_line.id,
                'credit_move_id': credit_line.id,
            })
        return partials_vals_list
