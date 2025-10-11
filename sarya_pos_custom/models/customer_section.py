from odoo import fields, models, api


class CustomerSection(models.Model):
    _inherit = 'customer.section'

    allow_outlet_transfer = fields.Boolean()