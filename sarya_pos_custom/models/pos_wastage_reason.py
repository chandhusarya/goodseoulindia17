# -*- coding: utf-8 -*-
from odoo import fields, models, api


class WastageReason(models.Model):
    _name = 'pos.wastage.reason'
    _description = 'Wastage Reason'
    _order = "sequence"

    name = fields.Char(
        string='Name',
        required=True
    )
    sequence = fields.Integer(
        string='Sequence',
        default=1
    )

    _sql_constraints = [('name_unique', 'unique (name)', "A FOC Reason with this name already exists")]

