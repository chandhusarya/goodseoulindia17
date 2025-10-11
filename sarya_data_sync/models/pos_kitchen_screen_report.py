# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PosKitchenScreenReport(models.Model):
    _name = 'pos.kitchen.screen.report'
    _description = 'kitchen screen Report'
    _order = 'id desc'
    _rec_name = 'pos_kitchen_screen_id'


    pos_kitchen_screen_id = fields.Char(
        string='Kitchen Screen',
        copy=False,
        required=True
    )
    pos_order_id = fields.Many2one(
        comodel_name='pos.order',
        string='POS Order Id',
        copy=False
    )
    pos_config_id = fields.Many2one(
        comodel_name='pos.config',
        related='pos_order_id.config_id'
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='pos_order_id.company_id'
    )
    bill_no = fields.Char(
        related='pos_order_id.tracking_number',
        string='BIll No'
    )
    receipt_no = fields.Char(
        related='pos_order_id.pos_reference',
        string='Receipt No'
    )
    pos_order_line_id = fields.Many2one(
        comodel_name='pos.order.line',
        string='Order Line Id',
        copy=False
    )
    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string='Product Template'
    )
    order_received_time = fields.Datetime(
        related='pos_order_id.date_order',
        string='Order Received Time',
    )
    preparation_done_time = fields.Datetime(
        string='Preparation Done Time',
        copy=False
    )
    preparation_time_duration = fields.Char(
        string='Preparation TIme Duration',
        help="Preparation Time Duration"
    )
    is_recall_done = fields.Boolean(
        string='Is Recall Done?',
        copy=False,
        default=False
    )
    local_rec_id = fields.Integer(
        string='Local Record Id',
        copy=False
    )