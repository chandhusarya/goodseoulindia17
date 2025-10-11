# -*- coding: utf-8 -*-
from odoo import fields, models


class TillAuditAndClosureLine(models.Model):
    _name = 'till.audit.and.closure.line'
    _description = 'Till Audit And Closure Line'
    _rec_name = 'till_audit_and_closure_id'

    till_audit_and_closure_id = fields.Many2one(
        comodel_name='till.audit.and.closure',
        string='Till Audit And Closure',
        ondelete='cascade'
    )
    pos_payment_method_id = fields.Many2one(
        comodel_name='pos.payment.method',
        string='Payment Type',
        required=True
    )
    actual_amount = fields.Float(
        string='Actual Amount'
    )
    system_amount = fields.Float(
        string='System Amount'
    )
    diff_amount = fields.Float(
        string='Diff. Amount'
    )
    remarks = fields.Char(
        string="Remarks"
    )
    sequence = fields.Integer(
        string="Sequence"
    )
    local_rec_id = fields.Integer(
        string='Local Record Id',
        copy=False
    )
