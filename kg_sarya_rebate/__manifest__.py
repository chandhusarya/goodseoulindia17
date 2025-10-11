# -*- coding: utf-8 -*-
{
    'name': "KG Sarya Rebate",

    'summary': """
        Rebate Flow in Pricelist""",

    'description': """
        Rebate Flow in Pricelist
    """,

    'author': "MINI K",
    'website': "http://www.klystronglobal.com",

    'category': 'Sales',
    'version': '17.10',
    'license': 'AGPL-3',

    'depends': ['base', 'product', 'account', 'kg_sarya', 'kg_sarya_inventory', 'mail', 'kg_sarya_vansales'],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',

        'views/rebate_form.xml',
        'views/res_config_settings.xml',
        'views/master_rebate.xml',
        'views/prg_rebate_realtime.xml',
        # 'views/rebate_master.xml',
        'views/shelf_rental.xml',
        'views/pricelist.xml',
        'views/rebate_entry_views.xml',
        'views/rebate_item_views.xml',
        # 'views/account_move_view.xml',
        'data/rebate_scheduler_template.xml',
        'reports/report.xml',
        'reports/rebate_simplified_report_template.xml',
        'reports/rebate_detailed_report_template.xml',
        'wizard/rebate_report_wizard_views.xml',
        'wizard/rebate_move_wizard_views.xml',
        'wizard/pricelist_wizard.xml',
    ],
}
