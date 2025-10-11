# -*- coding: utf-8 -*-
{
    'name': "sarya_pos_order_import",

    'summary': "Food Square order import",

    'description': """
Module to import order summary shared from Gofrugal POS of Food Square.
    """,

    'author': "Sarya",
    'website': "https://www.sarya.ae",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['sale', 'sales_team'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'view/sale_view.xml',
        'view/res_partner.xml',
        'wizard/daily_sales_view.xml',
    ],
}

