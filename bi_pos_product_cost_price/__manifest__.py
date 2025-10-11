# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
{
    'name': "Show Product Cost Price in POS Screen",
    'version': '17.0.0.0',
    'category': 'Point of Sale',
    'summary': "POS screen product cost price on pos screen show product cost price on point of sale screen product cost price visible pos product cost price show pos product cost price on pos screen cost price of product on pos screen point of sales product cost price",
    'description': """ 

        Product Cost Price in odoo,
        Show Product Cost on POS in odoo,
        Restrict Validate Order in odoo,
        Product Cost Price in odoo,
        Cost Price in POS Cart in odoo,

    """,
    "author": "BrowseInfo",
    "website" : "https://www.browseinfo.com",
    'depends': ['base', 'point_of_sale'],
    'data': [
       'views/pos_config.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'bi_pos_product_cost_price/static/src/app/product/models.js',
            'bi_pos_product_cost_price/static/src/app/product/orderwidget.js',
            'bi_pos_product_cost_price/static/src/app/payment/paymentscreen.js',
            'bi_pos_product_cost_price/static/src/app/product/orderwidget.xml',

            
        ],
    },
    'license': 'OPL-1',
    "auto_install": False,
    "installable": True,
    "live_test_url": "https://youtu.be/WRHmRu4FGCQ",
    "images":['static/description/Banner.gif'],
}
