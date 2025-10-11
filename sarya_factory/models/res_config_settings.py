# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompanyInherit(models.Model):
    _inherit = "res.company"

    lpo_approver_user_ids = fields.Many2many('res.users', relation='mrp_lpo_approver_rel', column1='config_id', column2='user_id', string='LPO Approvers')
    factory_analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account',
                                          help="Analytic account to be used for this Local Purchase.")


class ResConfigSettingsInherit(models.TransientModel):
    _inherit = 'res.config.settings'

    lpo_approver_user_ids = fields.Many2many(comodel_name='res.users', string='LPO Approvers', related='company_id.lpo_approver_user_ids', readonly=False)
    factory_analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', related='company_id.factory_analytic_account_id', readonly=False,
                                          help="Analytic account to be used for this POS.")
