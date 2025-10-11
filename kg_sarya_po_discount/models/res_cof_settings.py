# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompanyAccInherit(models.Model):
    _inherit = "res.company"

    acc_discount1_id = fields.Many2one('account.account', string='Discount Account 1')
    acc_discount2_id = fields.Many2one('account.account', string='Discount Account 2')


class ResConfigSettingsInherit(models.TransientModel):
    _inherit = 'res.config.settings'

    acc_discount1_id = fields.Many2one('account.account', related='company_id.acc_discount1_id',
                                       string='Discount Account 1', readonly=False)

    acc_discount2_id = fields.Many2one('account.account', related='company_id.acc_discount2_id',
                                       string='Discount Account 2', readonly=False)
