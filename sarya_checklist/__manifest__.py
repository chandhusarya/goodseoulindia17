# Copyright (C) Softhealer Technologies.
{
    "name": "Sarya Checklist",
    "author": "Sarya",
    "website": "www.sarya.com",
    "category": "POS",
    'license': 'AGPL-3',
    "summary": "",
    "version": "17.10",
    "depends": ['base', 'mail', 'point_of_sale'],

    "data": [
        'security/security.xml',
        'security/ir.model.access.csv',
        'report/outlet_checklist_template.xml',
        'views/checklist_config_views.xml',
        'views/responsible_master_views.xml',
        'views/outlet_checklist_views.xml',
        'views/menu.xml',
        'data/cron.xml',
    ],

    "images": [],
    "application": True,
    "auto_install": False,
    "installable": True,
}
