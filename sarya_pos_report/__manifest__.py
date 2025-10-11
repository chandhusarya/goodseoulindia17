# -*- coding: utf-8 -*-
{
    'name': "sarya_pos_report",

    'summary': "Sarya Reports",

    'description': """
    -Food cost report.
    """,

    'author': "Pranav",
    'website': "https://www.sarya.ae",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Point of Sale',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'point_of_sale', 'sarya_reports'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/pos_config.xml',
        'wizard/food_cost_report_view.xml',
        'wizard/daily_sales_report_view.xml',
        'report/point_of_sale_report.xml',
        'report/report_dailysales.xml',
    ],
}

