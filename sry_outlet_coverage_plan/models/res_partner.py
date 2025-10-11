from odoo import api, fields, models


class Partner(models.Model):
    _inherit = 'res.partner'

    short_name_merchandiser = fields.Char("Short Name for Merchandiser")