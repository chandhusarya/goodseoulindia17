from odoo import fields, models, api


class LocalPurchase(models.Model):
    _inherit = 'local.purchase'


    material_request_id = fields.Many2one(
        comodel_name='material.request',
        string='Material Request')
