
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from collections import OrderedDict
import io
from odoo.tools.misc import xlsxwriter

class SaryaReconcileLoadRebate(models.TransientModel):
    """Sarya Reconcile Load Rebate"""

    _name = 'sarya.reconcile.load.rebate'
    _description = 'Sarya Reconcile Load Rebate'


    reconcile_id = fields.Many2one('sarya.reconcile', string='Reconcile')
    rebate_from = fields.Date("Rebate From")
    rebate_to = fields.Date("Rebate To")

    def load_rebates(self):

        reconcile_id = self.reconcile_id

        search_condition = [('account_id.account_type', 'in', ('asset_receivable', 'liability_payable')),
                            ('move_id.state', '=', 'posted'), ('amount_residual', '!=', 0)]
        if reconcile_id.partner_id:
            search_condition.append(('partner_id', 'in', reconcile_id.partner_id.ids))
        if reconcile_id.master_parent_id:
            master_parent_partner_ids = self.env['res.partner'].search([
                ('master_parent_id', '=', reconcile_id.master_parent_id.id)])
            if master_parent_partner_ids:
                search_condition.append(('partner_id', 'in', master_parent_partner_ids.ids))

        if self.rebate_from:
            search_condition.append(('date', '>=', self.rebate_from))
        if self.rebate_to:
            search_condition.append(('date', '<=', self.rebate_to))

        #MOVE JOURNAL
        journal_id = self.env['ir.config_parameter'].sudo().get_param('kg_sarya_rebate.rebate_journal_id', False)
        print("4>>>>>>>>>>>>>>>>>>>>>>>>>>")
        if not journal_id:
            raise UserError(_("You must configure journal for rebate in settings"))
        journal_id = int(journal_id)
        search_condition.append(('move_id.journal_id', '=', journal_id))

        move_line = self.env['account.move.line'].search(search_condition)

        reconcile_id.journal_items_rebate_entries = False

        reconcile_id.journal_items_rebate_entries = move_line.ids

