from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    do_not_automate_invoice = fields.Boolean("Don't Automate Invoice Creation from Delivery")