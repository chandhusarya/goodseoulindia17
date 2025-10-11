from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    do_number = fields.Char('DO Number')
