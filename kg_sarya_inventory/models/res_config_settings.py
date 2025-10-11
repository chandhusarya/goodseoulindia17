# -*- coding: utf-8 -*-

from odoo import fields, models
from ast import literal_eval


class PromotionSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    leaflet_fee_account_id = fields.Many2one('account.account', string='Leaflet Fee Account',
                                             config_parameter='kg_sarya_inventory.leaflet_fee_account_id')
    rental_fee_account_id = fields.Many2one('account.account', string='Rental Fee Account',
                                            config_parameter='kg_sarya_inventory.rental_fee_account_id')
    promotion_journal_id = fields.Many2one('account.journal', string='Promotion Journal',
                                           config_parameter='kg_sarya_inventory.promotion_journal_id')

    email_notification_users = fields.Many2many('res.users', 'email_notification_users', 'user_id',
                                                'email_notification_user', string='Email Notification Users')
    lot_mail_users_ids = fields.Many2many('res.users', string='Email users For Lot Alert',
                                          related='company_id.lot_mail_users_ids', readonly=False)

    logistic_partner_expense_account_id = fields.Many2one(
        related='company_id.logistic_partner_expense_account_id',
        string="Logistic Partner Expense Account",
        readonly=False
    )
    logistic_partner_provision_account_id = fields.Many2one(
        related='company_id.logistic_partner_provision_account_id',
        string="Logistic Partner Provision Account",
        readonly=False
    )

    def set_values(self):
        res = super(PromotionSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('kg_sarya_inventory.email_notification_users',
                                                         self.email_notification_users.ids)
        return res

    def get_values(self):
        res = super(PromotionSettings, self).get_values()
        with_user = self.env['ir.config_parameter'].sudo()
        po_partner = with_user.get_param('kg_sarya_inventory.email_notification_users')
        res.update(email_notification_users=[(6, 0, literal_eval(po_partner))] if po_partner else [])
        return res


class ResCompanyAccInherit(models.Model):
    _inherit = "res.company"

    lot_mail_users_ids = fields.Many2many('res.users', string='Email users For Lot Alert')
    logistic_partner_expense_account_id = fields.Many2one(
        'account.account',
        string="Logistic Partner Expense Account"
    )
    logistic_partner_provision_account_id = fields.Many2one(
        'account.account',
        string="Logistic Partner Provision Account"
    )
