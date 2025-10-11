# -*- coding: utf-8 -*-
{
    'name': "Sarya Purchase Agreement",

    'summary': """
        Include Packaging in Purchase Agreement""",

    'description': """
        Include Packaging in Purchase Agreement
    """,
    'author': "MINI K",
    'website': "http://www.klystronglobal.com",
    'category': 'Purcahse',
    'version': '17.2',
    'depends': ['base', 'purchase', 'purchase_requisition', 'product'],
    'data': [
        'security/security.xml',
        'views/purchase_agreement.xml',
    ],
    'license': 'AGPL-3',

}
