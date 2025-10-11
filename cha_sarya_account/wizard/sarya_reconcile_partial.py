
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from collections import OrderedDict
import io
from odoo.tools.misc import xlsxwriter

class SaryaReconcilePartial(models.TransientModel):
    """Sarya Reconcile Partial"""

    _name = 'sarya.reconcile.partial'
    _description = 'Sarya Reconcile Partial'

    line_ids = fields.One2many('sarya.reconcile.partial.line', 'reconcile_partial_id')
    reconcile_summary_id = fields.Many2one('sarya.reconcile.summary', string='Reconcile Summary')
    partner_id = fields.Many2one('res.partner', string='Customer/Vendor')
    #payment_id = fields.Many2one('account.payment', string='Payment')
    payment_id = fields.Many2one('account.move.line', string='Payment')
    payment_amount_residual = fields.Float("Balance Amount in Payment")
    percentage_wise = fields.Float("Percentage for Auto Allocate")

    @api.onchange('payment_id')
    def _onchange_payment(self):
        if self.payment_id:
            self.payment_amount_residual = abs(self.payment_id.amount_residual)
        else:
            self.payment_amount_residual = 0


    def do_auto_allocation(self):
        if not self.payment_id:
            raise UserError(_('Payment is not selected'))

        if self.payment_amount_residual < 0.0001:
            raise UserError(_('There is no balance amount in payment'))

        total_due = 0
        for line in self.line_ids:
            total_due = total_due + line.amount_residual
        if total_due < 0.001:
            raise UserError(_('There is no due amount in selected invoices'))

        ratio = self.payment_amount_residual/total_due
        for line in self.line_ids:
            line.amount_to_reconcile = line.amount_residual * ratio

        context = self.env.context.copy()
        view_id = self.env.ref('cha_sarya_account.sarya_reconcile_partial_view').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Partial Allocation'),
            'view_mode': 'form',
            'res_model': 'sarya.reconcile.partial',
            'target': 'new',
            'res_id': self.id,
            'views': [[view_id, 'form']],
            'context': context,
        }

    def do_reconcile(self):
        if not self.payment_id:
            raise UserError(_('Payment is not selected'))

        if self.payment_amount_residual < 0.0001:
            raise UserError(_('There is no balance amount in payment'))

        total_amount_to_reconcile = 0
        for line in self.line_ids:
            total_amount_to_reconcile = total_amount_to_reconcile + line.amount_to_reconcile
            if line.amount_to_reconcile > line.move_id.amount_residual:
                user_msg = "Due amount of invoice %s is less than the amount to reconcile" % (line.move_id.name)
                raise UserError(_(user_msg))

        if total_amount_to_reconcile > self.payment_amount_residual:
            raise UserError(_('Total amount to Reconcile is higher than payment balance amount'))

        credit_line = self.payment_id
        #if self.payment_id and self.payment_id.state == 'posted':
        #    for move in self.payment_id.move_id:
        #        for item in move.line_ids:
        #            if item.account_id.user_type_id.name in ['Receivable', 'Payable']:
        #                if item.amount_residual != 0:
        #                    credit_line = item

        for line in self.line_ids:
            if line.amount_to_reconcile != 0:
                self.reconcile_summary_id.partial_reconcile([line.move_id], credit_line, line.amount_to_reconcile)





class SaryaReconcilePartialLine(models.TransientModel):

    _name = 'sarya.reconcile.partial.line'

    reconcile_partial_id = fields.Many2one('sarya.reconcile.partial', 'Van Summary Report')
    inv_date = fields.Date(string='Date')
    move_id = fields.Many2one('account.move.line', 'Journal Items')
    amount_residual = fields.Float("Due amount")
    amount_to_reconcile = fields.Float("Amount to Reconcile")











