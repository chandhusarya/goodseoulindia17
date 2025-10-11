from odoo import fields, models, api


class StockLocation(models.Model):
    _inherit = 'stock.location'

    is_factory = fields.Boolean(string='Factory Location', help='Mark if the location used for factory stock.')

    is_factory_storage_location = fields.Boolean(string='Factory Storage Location', help='Mark if the location used for storage of materials.')

    is_factory_production_location = fields.Boolean(string='Factory Production Location')

    is_factory_fryer_location = fields.Boolean(string='Factory Fryer Location')

    is_factory_grn_location = fields.Boolean(string='Factory GRN Location')

    is_factory_scrap_location = fields.Boolean(string='Factory Scrap')
