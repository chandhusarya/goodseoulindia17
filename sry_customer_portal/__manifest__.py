# -*- coding: utf-8 -*-
{
    'name': "Portal Sale Order",

    'summary': "Allow portal users to create Sales Orders",

    'description': """
Allow portal users to create Sales Orders
    """,

    'author': "Pranav",
    'website': "https://www.sarya.ae",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sales',
    'version': '17.0.1.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'product', 'sale', 'portal'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/portal_sale_order.xml',
        'views/portal_sale_order_failed.xml',
        'views/portal_menu.xml',
        'views/res_config_settings.xml',
    ],
}

