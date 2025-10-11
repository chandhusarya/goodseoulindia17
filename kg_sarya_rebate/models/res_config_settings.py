# -*- coding: utf-8 -*-

from odoo import fields, models


class Settings(models.TransientModel):
    _inherit = 'res.config.settings'
    rebate_journal_id = fields.Many2one('account.journal', string='Rebate Journal',
                                        config_parameter='kg_sarya_rebate.rebate_journal_id')
    rebate_provision_account_id = fields.Many2one('account.account', string='Rebate Credit Account',
                                                  config_parameter='kg_sarya_rebate.rebate_provision_account_id')
