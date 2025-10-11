from odoo import models, fields, api

class PvrLocationMaster(models.Model):
    _name = 'pvr.location.master'
    _description = 'PVR Location Master'

    name = fields.Char("Location Name", required=True)
    location_id = fields.Many2one(
        'stock.location', string="PVR Location")
    allowed_product_ids = fields.Many2many(
        'product.product', string="Products")
    allowed_user_ids = fields.Many2many(
        'res.users', string="Users")
    temp_location_id = fields.Many2one(
        "stock.location", string="Temporary Storage Location")
    container_products = fields.Many2many(
        'product.product',
        'pvr_container_products_rel',  # another relation table name
        'location_id', 'product_id',  # column names
        string="Container Products"
    )
    source_location_id = fields.Many2one(
        'stock.location', string="Source Location")
    pvr_management_location = fields.Many2one(
        'stock.location', string="PVR Management Location"
    )
    minimum_quantity_required = fields.Float(
        string='Minimum Quantity Required'
    )
    street = fields.Char("Street")
    street2 = fields.Char("Street2")
    city = fields.Char("City")
    state_id = fields.Many2one("res.country.state", "State")
    zip = fields.Char("ZIP")
    country_id = fields.Many2one("res.country", "Country")
    pan = fields.Char("PAN")
    vat = fields.Char("VAT")
    fssai_no = fields.Char("FSSAI No")

