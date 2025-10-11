# -*- coding: utf-8 -*-
from odoo import fields, models, _


class TillAssignAndClosure(models.Model):
    _name = 'till.assign.and.closure'
    _description = 'Till Assign And Closure'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(
        string="Name",
        required=True,
        readonly=True,
        default='New',
        copy=False
    )
    till_assign_date = fields.Datetime(
        string='Till Assign Date'
    )
    till_close_date = fields.Datetime(
        string='Till Close Date'
    )
    opening_notes = fields.Char(
        string='Till Assign Notes'
    )
    till_opening_cash = fields.Monetary(
        string="Till Opening Cash",
    )
    closing_notes = fields.Char(
        string='Till Closing Notes'
    )
    employee_name = fields.Char(
        string='Cashier'
    )
    opening_employee_name = fields.Char(
        string='Till Assigned By'
    )
    closing_employee_name = fields.Char(
        string='Till Closed By'
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        copy=False,
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='company_id.currency_id',
        string="Company Currency"
    )
    outlet_code = fields.Char(
        string='Outlet Code'
    )
    outlet_terminal_code = fields.Char(
        string='Outlet Terminal Code'
    )
    pos_config_id = fields.Many2one(
        comodel_name='pos.config',
        string="Outlet"
    )
    pos_session_id = fields.Many2one(
        comodel_name='pos.session',
        string="Session",
        required=True
    )
    state = fields.Selection(
        selection=[
            ('open', 'Open'),
            ('closed', 'Closed'),
        ],
        string='Status',
        required=True,
        readonly=True,
        copy=False,
        default='open',
    )
    till_audit_count = fields.Integer(
        compute='_compute_till_audit_count'
    )
    till_closure_count = fields.Integer(
        compute='_compute_till_closure_count'
    )
    local_rec_id = fields.Integer(
        string='Local Record Id',
        copy=False
    )

    def _compute_till_audit_count(self):
        till_audit_datas = self.env['till.audit.and.closure']._read_group([('till_assign_and_closure_id', 'in', self.ids), ('type', '=', 'audit')], ['till_assign_and_closure_id'], ['__count'])
        till_assign_and_closure_data = {till.id: count for till, count in till_audit_datas}
        for till in self:
            till.till_audit_count = till_assign_and_closure_data.get(till.id, 0)

    def _compute_till_closure_count(self):
        till_closure_datas = self.env['till.audit.and.closure']._read_group([('till_assign_and_closure_id', 'in', self.ids), ('type', '=', 'closure')], ['till_assign_and_closure_id'], ['__count'])
        till_assign_and_closure_data = {till.id: count for till, count in till_closure_datas}
        for till in self:
            till.till_closure_count = till_assign_and_closure_data.get(till.id, 0)

    def action_view_till_audit_records(self):
        return {
            'name': _('Till Audit'),
            'res_model': 'till.audit.and.closure',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('sarya_data_sync.till_audit_and_closure_list_view').id, 'list'),
                (self.env.ref('sarya_data_sync.till_audit_and_closure_form_view').id, 'form'),
                ],
            'type': 'ir.actions.act_window',
            'domain': [('till_assign_and_closure_id', 'in', self.ids), ('type', '=', 'audit')],
            'context': {'create': False}
        }

    def action_view_till_closure_records(self):
        return {
            'name': _('Till Closure'),
            'res_model': 'till.audit.and.closure',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('sarya_data_sync.till_audit_and_closure_list_view').id, 'list'),
                (self.env.ref('sarya_data_sync.till_audit_and_closure_form_view').id, 'form'),
                ],
            'type': 'ir.actions.act_window',
            'domain': [('till_assign_and_closure_id', 'in', self.ids), ('type', '=', 'closure')],
            'context': {'create': False}
        }