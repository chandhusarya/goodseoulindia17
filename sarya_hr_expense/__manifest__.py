# -*- coding: utf-8 -*-
{
    'name': "sarya_hr_expense",
    'summary': "",
    'description': """
        Hr expense Module
    """,

    'author': "Chandhu",
    'website': "https://www.sarya.ae",

    'category': 'HR',
    'version': '17.1',

    'depends': ['kg_sarya'],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/sarya_hr_menu.xml',
        'views/sarya_hr_expense.xml',
    ],

}

