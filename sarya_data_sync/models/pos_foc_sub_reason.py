# -*- coding: utf-8 -*-
from odoo import fields, models, api


class PosFocSubReason(models.Model):
    _name = 'pos.foc.sub.reason'
    _description = 'POS FOC Sub Reason'
    _order = "sequence"

    name = fields.Char(
        string='Name',
        required=True
    )
    sequence = fields.Integer(
        string='Sequence',
        default=1
    )
    pos_foc_reason_id = fields.Many2one(
        comodel_name='pos.foc.reason',
        string='POS FOC Reason',
        ondelete='cascade'
    )
