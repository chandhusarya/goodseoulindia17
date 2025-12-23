# -*- coding: utf-8 -*-
from odoo import fields, models, api


class PosFocReason(models.Model):
    _name = 'pos.foc.reason'
    _description = 'POS FOC Reason'
    _order = "sequence"

    name = fields.Char(
        string='Name',
        required=True
    )
    sequence = fields.Integer(
        string='Sequence',
        default=1
    )
    is_sub_reason_required = fields.Boolean(
        string="Sub Reason Required",
        default=False
    )
    foc_sub_reason_line_ids = fields.One2many(
        comodel_name='pos.foc.sub.reason',
        inverse_name='pos_foc_reason_id',
        string='Sub Reasons'
    )

    _sql_constraints = [('name_unique', 'unique (name)', "A FOC Reason with this name already exists")]
