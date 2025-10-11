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