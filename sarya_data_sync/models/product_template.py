# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    food_type = fields.Selection(
        selection=[
            ('veg', 'Vegetarian'),
            ('non_veg', 'Non-Vegetarian'),
        ],
        string="Food Type",
        help="Indicates the food type"
    )
    spice_level = fields.Selection(
        selection=[
            ('1', '1'),
            ('2', '2'),
            ('3', '3'),
            ('4', '4'),
            ('5', '5')
        ],
        string="Spice Level",
        help="Indicates the spice heaviness level of the dish"
    )
    receipt_product_name = fields.Char(
        string='Receipt Product Name',
        help='Customer Receipt product name',
        copy=False
    )
    kitchen_product_name = fields.Char(
        string='Kitchen Product Name',
        help='KDS, Kot product name',
        copy=False
    )
    product_name_kds_1 = fields.Char(
        string='Product Name KDS-1',
        help='KDS-1, product name',
        copy=False
    )
    product_name_kds_2 = fields.Char(
        string='Product Name KDS-2',
        help='KDS-2, product name',
        copy=False
    )
    product_name_kds_3 = fields.Char(
        string='Product Name KDS-3',
        help='KDS-3, product name',
        copy=False
    )
    product_name_kds_4 = fields.Char(
        string='Product Name KDS-4',
        help='KDS-4, product name',
        copy=False
    )
    product_name_kds_5 = fields.Char(
        string='Product Name KDS-5',
        help='KDS-5, product name',
        copy=False
    )
    product_name_kds_6 = fields.Char(
        string='Product Name KDS-6',
        help='KDS-6, product name',
        copy=False
    )

    @api.constrains('description_sale', 'available_in_pos')
    def _check_description_sale(self):
        for rec in self:
            if rec.available_in_pos and not rec.description_sale:
                raise ValidationError("Add Sales Description...")

