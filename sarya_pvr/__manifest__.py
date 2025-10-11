# -*- coding: utf-8 -*-
{
    'name': 'PVR Stock Management',
    'version': '1.0',
    'summary': 'Manage stock requests and availability for PVR locations.',
    'sequence': 10,
    'description': """
        Module to handle stock requests and monitor product availability at specific PVR stock locations.
    """,
    'category': 'Inventory/Stock',
    'depends': ['stock', 'product', 'base', 'sarya_hr', 'cha_sarya_purchase'], # Essential dependencies
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/ir_sequence_data.xml',
        'views/pvr_current_availibility_views.xml',
        'views/pvr_stock_request_views.xml',
        'views/pvr_portal_templates.xml',
        'views/pvr_location_master_views.xml',
        'views/container_request_views.xml',
        'views/close_container_request_views.xml',
        'views/container_transfer_pvr_views.xml',
        'views/stock_picking_views.xml',
        'data/report_paperformat.xml',
        'report/report_views.xml',
        'report/container_request_report_template_views.xml',
        'report/stock_request_delivery_challan.xml',
        'report/closing_session_report_template_views.xml',
        'report/damaged_closing_session_report_template_views.xml',
        'report/container_transfer_report_template_views.xml',
        'views/wastage_entry_pvr_views.xml',
    ],
}


