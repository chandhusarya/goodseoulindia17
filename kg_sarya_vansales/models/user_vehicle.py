# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class RouteVehicle(models.Model):
    _description = 'Vehicle'
    _name = 'user.vehicle'
    _inherit = ['mail.thread']
    _order = 'id asc'

    #@api.depends('brand', 'model', 'license_plate')
    #def _compute_vehicle_name(self):
    #    for record in self:
    #        record.name = (record.brand or '') + '/' + (record.model or '') + '/' + (
    #                record.license_plate or _('Plate No.'))

    name = fields.Char("Name")
    description = fields.Html("Vehicle Description", help="Add a note about this vehicle")
    active = fields.Boolean('Active', default=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.company,
    )
    image_128 = fields.Image("Logo", max_width=128, max_height=128)
    country_id = fields.Many2one('res.country', related='company_id.country_id')
    country_code = fields.Char("Country Code")
    license_plate = fields.Char(tracking=True, required=True,
                                help='License plate number of the vehicle')
    vin_sn = fields.Char('Chassis Number', help='Unique number written on the vehicle motor (VIN/SN number)',
                         copy=False)
    driver_id = fields.Many2one('res.users', 'Driver', tracking=True, help='Driver address of the vehicle',
                                copy=False)
    model = fields.Char('Model', tracking=True, required=True, help='Model of the vehicle')
    brand = fields.Char('Brand', readonly=False, required=True)
    color = fields.Char(help='Color of the vehicle')
    model_year = fields.Char('Model Year', help='Year of the model')

    location_id = fields.Many2one('stock.location', 'Location', domain="[('usage', '=', 'internal')]",
                                  help="Represents this vehicle's stock location. "
                                       "This location will be used for all transfers(load/unload) done from this vehicle")

    counterpart_location_id = fields.Many2one('stock.location', 'Load/Unload Location',
                                              domain="[('usage', '=', 'internal')]",
                                              help="Default location used for load/unload operations.")

    sales_picking_id = fields.Many2one('stock.picking.type', 'Sales Operation Type')

    payment_journal = fields.Many2one('account.journal', 'Payment Journal')

    sales_return_picking_id = fields.Many2one('stock.picking.type', 'Sales Return Type')

    non_saleable_location_id = fields.Many2one('stock.location', 'Non Saleable Location', domain="[('usage', '=', 'internal')]",
                                  help="Represents this vehicle's non saleable location. This will used stock items which cannot be sold")

    stock_adjustment_location = fields.Many2one('stock.location', 'Stock Adj Location',
                                  help="Stock adjustment during vehicle loading and unloading")

    scrap_location_unloading = fields.Many2one('stock.location', 'Scrap location for unloading')
    to_check_location_unloading = fields.Many2one('stock.location', 'To Check location for unloading')

    writeoff_account_id = fields.Many2one('account.account', string="WriteOff Account", copy=False,
                                          domain="[('deprecated', '=', False)]")

    stock_for_load_request = fields.Many2one('stock.location', 'Stock Location for for load request', domain="[('usage', '=', 'internal')]")



    def update_reserved_qty_in_quants(self):
        location = self.location_id
        stock_quants = self.env['stock.quant'].search([('location_id', "=", location.id)])
        for sq in stock_quants:
                sq.reserved_quantity = 0


