# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompanyInherit(models.Model):
    _inherit = "res.company"

    acc_sales_return_id = fields.Many2one('account.account', string='Sales Return Account')


class ResConfigSettingsInherit(models.TransientModel):
    _inherit = 'res.config.settings'

    acc_sales_return_id = fields.Many2one('account.account', related='company_id.acc_sales_return_id',
                                          string='Sales Return Account', readonly=False)
