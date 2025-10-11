# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompanyInherit(models.Model):
    _inherit = "res.company"

    local_purchase_journal_id = fields.Many2one('account.journal', string='Local Purchase Journal')
    office_analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account',
                                                  help="Analytic account to be used for this Office Purchase.")


class ResConfigSettingsInherit(models.TransientModel):
    _inherit = 'res.config.settings'

    local_purchase_journal_id = fields.Many2one('account.journal', string='Local Purchase Journal', related='company_id.local_purchase_journal_id', readonly=False)
    office_analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account',
                                                  related='company_id.office_analytic_account_id', readonly=False,
                                                  help="Analytic account to be used for this POS.")


