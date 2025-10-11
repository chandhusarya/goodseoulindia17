# -*- coding: utf-8 -*-
{
    'name': "KG Purchase Order",

    'summary': """
    Sale module customizations
        """,
    'description': """
        Purchase module customizations
    """,
    'author': "SHARMI SV",
    'website': "http://www.klystronglobal.com",
    'category': 'Purchase',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','purchase'],

    # always loaded
    'data': [
        'report/paper_format_purchase.xml',
        'report/purchase_order_report.xml',
        'report/purchase_order_report_template.xml',
        'views/purchase_order_view.xml',
    ],
}
