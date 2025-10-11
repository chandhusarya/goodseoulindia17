# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class PosSession(models.Model):
    _inherit = 'pos.session'

    local_rec_id = fields.Integer(
        string='Local Record Id',
        copy=False
    )
    till_assign_and_closure_count = fields.Integer(
        compute='_compute_till_assign_and_closure_count'
    )
    cash_statement_count = fields.Integer(
        compute='_compute_cash_statement_count'
    )

    def _compute_till_assign_and_closure_count(self):
        till_assign_and_closure_datas = self.env['till.assign.and.closure']._read_group([('pos_session_id', 'in', self.ids)], ['pos_session_id'], ['__count'])
        sessions_data = {session.id: count for session, count in till_assign_and_closure_datas}
        for session in self:
            session.till_assign_and_closure_count = sessions_data.get(session.id, 0)

    def _compute_cash_statement_count(self):
        cash_statement_datas = self.env['cash.statement']._read_group([('pos_session_id', 'in', self.ids)], ['pos_session_id'], ['__count'])
        sessions_data = {session.id: count for session, count in cash_statement_datas}
        for session in self:
            session.cash_statement_count = sessions_data.get(session.id, 0)

    def action_view_till_assign_and_closure_records(self):
        return {
            'name': _('Till Assign And Closure'),
            'res_model': 'till.assign.and.closure',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('sarya_data_sync.till_assign_and_closure_list_view').id, 'list'),
                (self.env.ref('sarya_data_sync.till_assign_and_closure_form_view').id, 'form'),
                ],
            'type': 'ir.actions.act_window',
            'domain': [('pos_session_id', 'in', self.ids)],
            'context': {'create': False}
        }

    def action_view_cash_statement_records(self):
        return {
            'name': _('Cash Statements'),
            'res_model': 'cash.statement',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('sarya_data_sync.cash_statement_list_view').id, 'list'),
                (self.env.ref('sarya_data_sync.cash_statement_form_view').id, 'form'),
                ],
            'type': 'ir.actions.act_window',
            'domain': [('pos_session_id', 'in', self.ids)],
            'context': {'create': False}
        }

    def _post_statement_difference(self, amount, is_opening):
        return
