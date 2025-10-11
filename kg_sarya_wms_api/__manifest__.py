# -*- coding: utf-8 -*-
{
    'name': "KG Sarya WMS API Mixin",
    'summary': """
        Common logic-oriented functions to communicate with external APIs.""",
    'description': """
        Common logic-oriented functions to communicate with external APIs.
    """,
    'author': "Ashish",
    'license': 'AGPL-3',
    'website': "www.klystronglobal.com",
    'category': 'Uncategorized',
    'version': '17.2',
    'depends': ['base', 'product', 'account', 'sale','kg_sarya_inventory','stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/shipment_alert_template.xml',
        
        'views/res_company.xml',
        'views/product.xml',
        'views/shipment_advise.xml',
        'views/ir_config_settings.xml',

        'wizard/stock_details.xml',
    ],
}
