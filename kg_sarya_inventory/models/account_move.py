# -*- coding: utf-8 -*-

from odoo import models, fields, _, api
from odoo.exceptions import UserError
from ast import literal_eval


class AccountMove(models.Model):
    _inherit = 'account.move'

    promotion_id = fields.Many2one('promotion.entry')
    promotion_line_id = fields.Many2one('promotion.entry.lines')
    user_config = fields.Many2one('res.users')
    shipment_bill_number = fields.Char('Shipment Bill Number')

    pod_status = fields.Selection([('pending', 'Pending'),
                                   ('received', 'Received')],
                                  default='pending',
                                  string='POD Status',
                                  copy=False, tracking=True)

    delivery_status_actual = fields.Selection([('ready_for_delivery', 'Ready for delivery'),
                                        ('out_for_delivery', 'Dispatched'),
                                        ('delivered', 'Delivered'),
                                        ('not delivered', 'Not delivered'),
                                        ('cancel', 'Cancelled')], default='ready_for_delivery', tracking=True)

    pod_attach_ids = fields.Many2many('ir.attachment', 'sarya_invoice_pod_attach_rel', 'pick_id', 'attach_id',
                                      string="POD Attachments")

    pod_attached_date = fields.Date(string="POD Attached Date")

    def get_email_to(self):
        config_user_list = self.env['ir.config_parameter'].sudo().get_param(
            'kg_sarya_inventory.email_notification_users', self.user_config)
        mail_list = []
        if not config_user_list:
            raise UserError(
                _("Email Notification Users is Empty,\n please specify in Inventory Configuration settings"))
        for i in literal_eval(config_user_list):
            users = self.env['res.users'].search([('id', '=', i)])
            mail_list.append(users.partner_id.email)
        return " , ".join(mail_list)

    @api.constrains('invoice_date')
    def _check_delivery_date(self):
        for move in self:
            if move.move_type == 'out_invoice' and move.invoice_date and False:
                if move.invoice_date != move.delivery_date:
                    move.invoice_date = False
                    raise UserError(_('Invoice date should be same as delivery date'))

    @api.onchange('partner_id')
    def set_sale_person(self):
        if self.partner_id:
            self.invoice_user_id = self.partner_id.account_manager_id.id

    def correct_cogs_entry_for_returns(self):
        print("sddddddddddddddd")
