# -*- coding: utf-8 -*-

from odoo import fields, models
from ast import literal_eval


class CustomerPortalSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    quote_approval_mail_users_ids = fields.Many2many('res.users', string='Email users For Quotation Approval',
                                          related='company_id.quote_approval_mail_users_ids', readonly=False)



class ResCompanySalesInherit(models.Model):
    _inherit = "res.company"

    quote_approval_mail_users_ids = fields.Many2many('res.users', 'portal_quote_company_user2_rel', 'portal_quote_conf_id', 'user_id', string='Email users For Quotation Approval')
