# -*- coding: utf-8 -*-
{
    'name': "Sarya factory Customizations",

    'summary': "Sarya factory Customizations",

    'description': """
        Sarya Factory customizations
    """,

    'author': "Chandhu",
    'website': "https://www.sarya.ae",

    'category': 'Mrp',
    'version': '17.1',

    # any module necessary for this one to work correctly
    'depends': ['mrp', 'kg_sarya', 'cha_sarya_purchase', 'stock', 'web'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'views/local_purchase.xml',
        'views/material_request_view.xml',

        'views/production_request_view.xml',

        'report/report_material_request.xml',
        'report/material_requirement_report.xml',
        'views/stock_location.xml',
        'views/bom_item_view.xml',
        'views/mrp_bom_view.xml',
        'views/mrp_production_view.xml',
        'views/mrp_stock_transfer_view.xml',
        'views/res_config_settings.xml',
        'wizard/material_availability_wizard_view.xml',
        'data/sequence.xml',
    ],
  
}

