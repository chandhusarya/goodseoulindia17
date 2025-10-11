# -*- coding: utf-8 -*-
{
    'name': "Invoice on Delivery",

    'summary': """
        Option for invoice generation from delivery""",

    'description': """
        Option for invoice generation from delivery
    """,

    'author': "MINI K",
    'website': "www.klystronglobal.com",

    'category': 'Accounting',
    'version': '17.10',
    'license': 'AGPL-3',

    'depends': ['base','stock','sale','sale_stock'],

    'data': [
        'views/validate.xml',
        'views/res_partner_view.xml',
        'views/account_move_view.xml',
    ],
}
