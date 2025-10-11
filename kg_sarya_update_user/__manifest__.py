# -*- coding: utf-8 -*-
{
    'name': "KG Sarya Update User",

    'summary': """
        KG Sarya Update User by Approving
        """,

    'description': """
        KG Sarya Update User by Approving
    """,

    'author': "Mini k",
    'license': 'AGPL-3',
    'website': "http://www.klystronglobal.com",

    'category': 'Partner',
    'version': '17.2',

    # any module necessary for this one to work correctly
    'depends': ['base','mail','kg_sarya'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',

        'data/ir_sequence.xml',
        'views/user_approve.xml',
    ],

}
