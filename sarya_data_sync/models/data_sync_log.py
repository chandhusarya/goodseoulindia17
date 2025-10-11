# -*- coding: utf-8 -*-
from odoo import fields, models, api
import logging

from odoo.addons.test_impex.tests.test_load import message

_logger = logging.getLogger(__name__)


class DataSyncLog(models.Model):
    _name = 'data.sync.log'
    _description = 'Data Sync log'
    _order = 'id desc'

    name = fields.Char(
        string='Name',
        copy=False,
        required=True
    )
    log_type = fields.Selection(
        selection=[
            ('success', 'Success'),
            ('failed', 'Failed'),
            ('requested', 'Requested'),
        ],
        string='Log Type',
        copy=False
    )
    transfer_type = fields.Selection(
        selection=[
            ('data_pull', 'Data Pull'),
            ('data_push', 'Data Push')
        ],
        string='Transfer Type',
        copy=False
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        copy=False
    )
    outlet_code = fields.Char(
        string='Outlet',
        copy=False
    )
    model_name = fields.Char(
        string='Model Name',
        copy=False
    )
    message = fields.Char(
        string='Message',
        copy=False
    )

    @api.model
    def data_sync_request(self, model, fields, domain, config_domain, outlet_code):
        try:
            if model not in ('product.category', 'pos.category'):
                if self.env.user and self.env.user.company_id:
                    domain += [('company_id', '=', self.env.user.company_id.id)]
                if model in ('product.template', 'pos.payment.method', 'product.pricelist', 'product.pricelist.item'):
                    terminals = self.env['pos.config'].sudo().search(config_domain)
                    product_template_ids = []
                    payment_method_ids = []
                    price_list_ids = []
                    price_list_item_ids = []
                    for rec in terminals:
                        payment_method_ids += rec.payment_method_ids.ids
                        price_list_ids += rec.available_pricelist_ids.ids
                        for price_list in rec.available_pricelist_ids:
                            price_list_item_ids += price_list.item_ids.filtered(
                                lambda item: item.company_id == self.env.user.company_id).ids
                            product_template_ids += price_list.item_ids.filtered(
                                lambda item: item.company_id == self.env.user.company_id).mapped('product_tmpl_id').ids
                    if model == 'product.template':
                        domain += [('id', 'in', product_template_ids)]
                    if model == 'pos.payment.method':
                        domain += [('id', 'in', payment_method_ids)]
                    if model == 'product.pricelist':
                        domain += [('id', 'in', price_list_ids)]
                    if model == 'product.pricelist.item':
                        domain += [('id', 'in', price_list_item_ids)]
            records = self.env[model].sudo().search_read(domain, fields)
            return records
        except Exception as e:
            message = f"Error syncing model {model}: {e}"
            create_vals = {
                'name': 'Failed!!!!!!',
                'log_type': 'failure',
                'transfer_type': 'data_pull',
                'model_name': model,
                'message': message,
                'outlet_code': outlet_code,
                'company_id': self.env.user.company_id.id
            }
            self.create(create_vals)
            self.send_mail(message)
            _logger.error(f"Error syncing model {model}: {e}")

    @api.model
    def send_mail(self, message):
        cloud_pos_managers = self.env['res.users'].sudo().search(
            [('groups_id', '=', self.env.ref('point_of_sale.group_pos_manager').id)])

        mail_template = self.env.ref('sarya_data_sync.cloud_email_template_for_data_sync_error_sending')

        for user in cloud_pos_managers:
            employee = self.env['hr.employee'].search([('user_id', '=', user.id)])
            if employee and employee.work_email:
                mail_template.sudo().send_mail(self.id, force_send=True,
                                               email_values={'email_to': employee.work_email,
                                                             'subject': "Data Sync Failed!!!!!!",
                                                             'email_from': self.env.user.email or '',
                                                             'body_html': message})
        return True
