# -*- coding: utf-8 -*-
from odoo import fields, models


class TillAuditAndClosure(models.Model):
    _name = 'till.audit.and.closure'
    _description = 'Till Audit And Closure'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(
        string="Name",
        required=True,
        readonly=True,
        default='New',
        copy=False
    )
    type = fields.Selection(
        selection=[
            ('audit', 'Audit'),
            ('closure', 'Closure'),
        ],
        string='Type',
        required=True,
        readonly=True
    )
    employee_name = fields.Char(
        string='Cashier'
    )
    manager_name = fields.Char(
        string='Manager'
    )
    till_assign_and_closure_id = fields.Many2one(
        comodel_name='till.assign.and.closure',
        string='Till Assign And Closure',
        required=True,
        readonly=True
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        related='till_assign_and_closure_id.company_id'
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='company_id.currency_id',
        string="Company Currency"
    )
    outlet_code = fields.Char(
        string='Outlet Code',
        related='till_assign_and_closure_id.outlet_code'
    )
    outlet_terminal_code = fields.Char(
        string='Outlet Terminal Code',
        related='till_assign_and_closure_id.outlet_terminal_code'
    )
    pos_config_id = fields.Many2one(
        comodel_name='pos.config',
        string="Outlet",
        related='till_assign_and_closure_id.pos_config_id'
    )
    pos_session_id = fields.Many2one(
        comodel_name='pos.session',
        string="Session",
        required=True,
        related='till_assign_and_closure_id.pos_session_id'
    )
    till_audit_and_closure_line_ids = fields.One2many(
        comodel_name='till.audit.and.closure.line',
        inverse_name='till_audit_and_closure_id',
        string='Lines'
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('lines_computed', 'Lines Computed'),
            ('confirm', 'Confirm'),
            ('difference', 'Difference'),
            ('sent_for_approval', 'Sent for Approval'),
            ('done', 'Done')
        ],
        string='Status',
        required=True,
        readonly=True,
        copy=False,
        default='draft',
        tracking=True
    )
    till_assign_date = fields.Datetime(
        string='Till Assign Date',
        related='till_assign_and_closure_id.till_assign_date'
    )
    till_audit_date = fields.Datetime(
        string='Till Audit Date'
    )
    till_closure_date = fields.Datetime(
        string='Till Closure Date'
    )
    local_rec_id = fields.Integer(
        string='Local Record Id',
        copy=False
    )
    approved_by = fields.Char(
        string="Approved By",
        readonly="True"
    )
    approved_time = fields.Datetime(
        string="Approved Time",
        readonly="True"
    )
    cash_amount_count_html = fields.Html(
        string="Currency Count",
        sanitize=False
    )
    total_cash_amount = fields.Float(
        string="Total Cash Amount",
        store=True
    )