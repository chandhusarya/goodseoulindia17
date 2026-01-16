# -*- coding: utf-8 -*-
from odoo import fields, models, _


class PosOrder(models.Model):
    _inherit = 'pos.order'

    outlet_code = fields.Char(
        string='Outlet Code',
        copy=False,
        readonly=True
    )
    local_rec_id = fields.Integer(
        string='Local Record Id',
        copy=False
    )
    pos_order_type_id = fields.Many2one(
        comodel_name='pos.order.type',
        string='Order Type',
        copy=False
    )
    is_delivery_order = fields.Boolean(
        string='Delivery Order',
        related='pos_order_type_id.is_home_delivery'
    )
    buzzer_number = fields.Char(
        string='Token Number',
        copy=False
    )
    foc_reason_id = fields.Many2one(
        comodel_name='pos.foc.reason',
        string="FOC Reason",
        copy=False
    )
    foc_sub_reason_id = fields.Many2one(
        comodel_name='pos.foc.sub.reason',
        string="FOC Sub Reason",
        copy=False
    )
    is_foc_pricelist = fields.Boolean(
        string='Is FOC Pricelist?',
        related='pricelist_id.is_foc_pricelist'
    )
    payment_change_notes = fields.Html(
        string="Payment Change Notes",
        copy=False,
        sanitize=True
    )

    def action_view_kitchen_order_report(self):
        return {
            'name': _('POS Kitchen Screens Report'),
            'res_model': 'pos.kitchen.screen.report',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('sarya_data_sync.pos_kitchen_screen_report_list_view').id, 'list'),
                (self.env.ref('sarya_data_sync.pos_kitchen_screen_report_form_view').id, 'form'),
            ],
            'type': 'ir.actions.act_window',
            'domain': [('pos_order_id', 'in', self.ids)],
            'context': {'create': False, 'edit': False, 'search_default_group_by_pos_kitchen_screen_id': 1}
        }