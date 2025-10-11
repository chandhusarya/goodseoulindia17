from odoo import fields, models, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer')
