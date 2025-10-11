from odoo import fields, models, api


class ResCountryState(models.Model):
    _inherit = 'res.country.state'

    gst_code = fields.Char(string="GST Code")
