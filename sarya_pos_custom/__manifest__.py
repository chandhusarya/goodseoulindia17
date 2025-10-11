# -*- coding: utf-8 -*-
{
    'name': "sarya_pos_custom",

    'summary': "POS Module customization",

    'description': """
-Hide Lot selection popup.
    """,

    'author': "Pranav",
    'website': "https://www.sarya.ae",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Point of Sale',
    'version': '17.1',

    # any module necessary for this one to work correctly
    'depends': ['point_of_sale', 'pos_preparation_display', 'cha_sarya_purchase'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/stock_inventory_view.xml',
        'views/wastage_calculation.xml',
        'views/pos.xml',
        'views/local_purchase_inherit.xml',
        'data/sequence.xml',
        'views/menus.xml',
        'views/customer_section_views.xml',
        'views/outlet_transfer_views.xml',
        'views/stock_picking_views.xml',
        # 'views/res_users_views.xml',
        'views/res_users_pos_allowed.xml',
        'views/pos_payment_views.xml',
        'views/pos_session_views.xml',
        'views/pos_order_view.xml'
    ],
    'assets': {
        'pos_preparation_display.assets': [
            'sarya_pos_custom/static/src/models/preparation/order.js',
            'sarya_pos_custom/static/src/models/order.js',
        ],
        'point_of_sale._assets_pos': [
            # 'sarya_pos_custom/static/src/models/models.js',
        ],
    },
}

