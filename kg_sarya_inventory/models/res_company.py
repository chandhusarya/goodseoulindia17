from odoo import fields, models, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    company_type = fields.Selection(
        string='Company Type',
        selection=[('retail', 'Retail'),
                   ('distribution', 'Distribution'), ],
        default='retail', help='This is to differentiate the company for goods receipt.')

