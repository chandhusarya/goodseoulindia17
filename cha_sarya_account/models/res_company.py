from odoo import fields, models, api


class ResCompany(models.Model):
    _inherit = 'res.company'
    _description = 'Company'

    pan_no = fields.Char(
        string='PAN No.')
    cin_no = fields.Char(
        string='CIN No.')
    fssai_no = fields.Char(
        string='FSSAI No.')
