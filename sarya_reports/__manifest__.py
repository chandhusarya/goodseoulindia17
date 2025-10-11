# -*- coding: utf-8 -*-
{
    'name': "sarya_reports",

    'summary': "Accounting Reports",

    'description': """
-Tax Invoice
    """,

    'author': "Sarya",
    'website': "https://www.sarya.ae",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account_accountant', 'cha_sarya_account', 'web', 'stock'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'report/delivery_challan_template.xml',
        'report/tax_invoice_report_distributor_template.xml',
        'report/tax_invoice_report_retailer_template.xml',
        'report/proforma_invoice_report_template.xml',
        'report/reports.xml',
        'report/stock_report_view.xml',
        # 'views/company_banner_view.xml',
    ],
}

