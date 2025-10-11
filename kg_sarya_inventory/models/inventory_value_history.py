from odoo import models, fields, _, api
from odoo.exceptions import UserError


class InventoryValueHistory(models.Model):
    _name = 'inventory.value.history'

    as_of_date = fields.Datetime('Date', default=fields.Datetime.now())

    product_id = fields.Many2one('product.product', string='Product')

    quantity = fields.Float('Quantity', digits=(10, 7))

    ctn_quantity = fields.Float("Ctn Quantity", digits=(10, 7))

    lot_id = fields.Many2one('stock.lot', 'Lot')

    location_id = fields.Many2one('stock.location', 'Location')

    location_name = fields.Char(related="location_id.name", store=True, string='Location Name')

    brand = fields.Many2one('product.manufacturer', 'Brand')

    categ_id = fields.Many2one('product.category', 'Product Category')

    section = fields.Many2one('customer.section', string="Customer Section")

    value = fields.Float("Value")


    def update_inventory_value(self):


        all_stock = self.env['stock.quant'].search([('quantity', '!=', 0), ('location_id.usage', 'in', ('internal', 'transit'))])

        for quant in all_stock:

            item_unit_value = quant.lot_id.final_cost
            if item_unit_value < 0.000000001:
                item_unit_value = quant.product_id.manual_cost_for_zero_cost_item

            value = quant.quantity * item_unit_value

            ctn_packaging_id = self.env['product.packaging'].search([('product_id', '=', quant.product_id.id)], order='qty desc', limit=1)

            ctn_quantity = quant.quantity/ctn_packaging_id.qty

            vals = {
                'product_id': quant.product_id.id,
                'quantity': quant.quantity,
                'ctn_quantity': ctn_quantity,
                'lot_id': quant.lot_id.id,
                'location_id': quant.location_id.id,
                'brand': quant.product_id.brand and quant.product_id.brand.id,
                'categ_id': quant.product_id.categ_id and quant.product_id.categ_id.id,
                'section': quant.product_id.section and quant.product_id.section.id,
                'value': value
            }
            self.env['inventory.value.history'].create(vals)
