# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
from odoo.tools import float_repr, format_datetime


class PricelistShelfRental(models.Model):
    _inherit = "product.pricelist"


    shelf_item_ids = fields.One2many(
        'product.shelf.item', 'shelf_id', 'Shelf Rental',
        copy=True)


class ShelfRentalItem(models.Model):
    _name = "product.shelf.item"
    _description = "Shelf Rental for Product Category"


    product_tmpl_id = fields.Many2one(
        'product.template', 'Product', ondelete='cascade', check_company=True,
        help="Specify a template if this rule only applies to one product template. Keep empty otherwise.")
    shelf_id = fields.Many2one('product.pricelist')
    categ_id = fields.Many2one(
        'product.category', 'Product Category', ondelete='cascade',
        help="Specify a product category if this rule only applies to products belonging to this category or its children categories. Keep empty otherwise.")
    uom = fields.Many2one('uom.uom', 'Unit')
    amount = fields.Float(help="Shelf rental amount/unit")
    applied_on = fields.Selection([
        ('2_product_category', 'Product Category'),('1_product','Product')], "Apply On",
        default='2_product_category', required=True,
        help='Shelf Rental Item applicable on selected option')
    name = fields.Char(compute='_get_name_applied',
        help="Explicit rule name for this Shelf Rental line.")

    company_id = fields.Many2one(
        'res.company', 'Company',
        readonly=True, related='shelf_id.company_id', store=True)
    currency_id = fields.Many2one(
        'res.currency', 'Currency',
        readonly=True, related='shelf_id.currency_id', store=True)

    @api.depends('applied_on', 'categ_id', 'product_tmpl_id','shelf_id')
    def _get_name_applied(self):
        print("hininini")
        for item in self:
            print("inside------------------>")
            if item.categ_id and item.applied_on == '2_product_category':
                item.name = _("Category: %s") % (item.categ_id.display_name)
            elif item.product_tmpl_id and item.applied_on == '1_product':
                item.name = _("Product: %s") % (item.product_tmpl_id.display_name)
