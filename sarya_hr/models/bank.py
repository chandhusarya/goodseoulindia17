from odoo import fields, models, api


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    account_type = fields.Selection(
        string='Account Type',
        selection=[('current', 'Current'), 
                   ('savings', 'Savings'), ], default='current')

        
