# -*- coding: utf-8 -*-
{
    'name': "sarya_stock_check",

    'summary': "Sarya inventory check",

    'description': """
Module helps in daily, weekly and monthly stock check for items.
    """,

    'author': "Sarya",
    'website': "https://www.sarya.in",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Inventory/Inventory Control',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['sarya_pos_custom'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/stock_check_plan_view.xml',
    ],
}

