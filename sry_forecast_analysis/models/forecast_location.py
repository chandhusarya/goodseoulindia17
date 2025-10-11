from odoo import models,fields,api,_

class sry_forecast_location(models.Model):
    _name = 'sry.forecast.location'

    name = fields.Char(string="Name")
    location_ids = fields.Many2many('stock.location', 'sry_forecast_location_stock_location_rel', string="Locations")
    total = fields.Boolean(string="Total")
    report = fields.Selection([('soh','SOH'),('forecast','FORECAST')], string='Report')
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company', default=lambda self: self.env.company)

