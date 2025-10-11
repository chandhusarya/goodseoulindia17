# -*- coding: utf-8 -*-
from odoo import fields, models


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    is_hold_preparation_product = fields.Boolean(
        string='Is Hold Preparation Product?',
        default=False,
        copy=False
    )
    recall_done_time = fields.Datetime(
        string='Recall Done Time',
        copy=False
    )
    onhold_release_time = fields.Datetime(
        string='Onhold Release Time',
        copy=False
    )
    local_rec_id = fields.Integer(
        string='Local Record Id',
        copy=False
    )
