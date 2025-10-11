{
    "name": "Sarya Outlet Coverage Plan",
    "version": "17.10",
    'license': 'AGPL-3',
    "author": "Sarya",
    "website": "www.sarya.com",
    "summary": "Sarya Outlet Coverage Plan for Merchandisers",
    "description": """Sarya Outlet Coverage Plan for Merchandisers""",
    "depends": ["base", "account", "kg_sarya_update_user"],
    "data": [
             "security/ir.model.access.csv",
             "wizard/load_customer_wizard_view.xml",
             "views/coverage_master_view.xml",
             "views/coverage_plan_view.xml",
             "views/portal_template.xml",
             "views/res_partner.xml",
             "views/coverage_master_line_view.xml",
             "wizard/change_merchandiser_view.xml"
             ],
    "license": "LGPL-3",
    # 'assets': {
    #     'web.assets_frontend': [
    #         'sry_outlet_coverage_plan/static/src/js/appointment_select_appointment_slot.js',
    #         'sry_outlet_coverage_plan/static/src/scss/appointment.scss',
    #     ],
    # },
    "installable": True,
    "auto_install": False,
}
