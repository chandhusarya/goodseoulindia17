# Copyright (C) Softhealer Technologies.
{
    "name": "Post Dated Cheque Management",
    "author": "Chandhu",
    "website": "www.sarya.com",
    "category": "Accounting",
    'license': 'AGPL-3',
    "summary": "",
    "version": "17.10",
    "depends": [
        "account"
    ],

    "data": [
        "security/security.xml",
        "data/account_data.xml",
        "data/cron_scheduler_ven.xml",
        "data/mail_template.xml",
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/pdc_payment_wizard.xml",
        "views/views.xml",
        "views/report_pdc_payment.xml",
    ],

    "images": ['static/description/background.png', ],
    "application": True,
    "auto_install": False,
    "installable": True,
}
