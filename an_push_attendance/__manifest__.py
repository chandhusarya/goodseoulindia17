# -*- coding: utf-8 -*-
{
    'name': 'ZKTeco, ESSL & ADMS Push Attendance Integration',
    'summary': 'Real-time ZKTeco, ESSL & ADMS Push Protocol Integration - BioTime Replacement - No IP/DNS Required',
    'description': """Real-time attendance tracking with ZKTeco, ESSL and any device supporting ADMS Push SDK - Complete BioTime Replacement - No IP or DNS configuration required!

Key Features:
* Real-time attendance tracking without IP/DNS configuration
* Support for ZKTeco Push Protocol devices
* Full ESSL biometric device integration
* Compatible with any device supporting ADMS Push SDK
* Perfect BioTime software replacement
* Automatic employee synchronization
* Real-time attendance logging
* Fingerprint and face template management
* Advanced biometric verification policies
* Device command management
* Multi-device support
* Batch attendance processing
* Detailed operation logging
* Advanced security features""",
    'category': 'Human Resources/Attendance',
    'version': '17.0.1.0.4',
    'author': 'Ahmed Nour',
    'website': 'https://odoosa.net',
    'license': 'LGPL-3',
    # Remove 'support' key - use maintainer instead
    'maintainer': 'Ahmed Nour <ahmednour@outlook.com>',
    'price': 350,
    'currency': 'USD',
    # Simplify images to just banner image which is standard in Odoo 18
    'images': ['static/description/banner.gif'],
    'depends': ['base', 'hr', 'hr_attendance'],
    'data': [
        # Security files first
        'security/security.xml',
        'security/ir.model.access.csv',
        
        # Data files
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'data/cron_data.xml',
        'data/attendance_record_actions.xml',
        'data/attendance_process_cron.xml',
        'data/attendance_config_settings_data.xml',
        
        # Views with action definitions first
        'views/attendance_device_views.xml',
        'views/attendance_record_views.xml',
        'views/attendance_process_views.xml',
        'views/biometric_data_views.xml',
        'views/config_settings_views.xml',
        'views/device_command_views.xml',
        'views/device_user_views.xml',
        'views/face_template_views.xml',
        'views/fingerprint_template_views.xml',
        'views/fp_status_policy_views.xml',
        'views/operation_log_views.xml',
        'views/resource_calendar_views.xml',
        'views/user_picture_views.xml',
        'views/hr_employee_views.xml',
        
        # Wizard views
        'wizard/attendance_recheck_wizard_views.xml',
        
        # Menu items after actions are defined
        'views/menu_items.xml',
        
        # Additional menus that depend on parent menus
        'views/biometric_data_menu.xml',
    ],
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
    'pre_uninstall_hook': 'pre_uninstall_hook',
    'installable': True,
    'application': True,
    'auto_install': False,
    'demo': [],
    # Remove live_test_url which may not be supported in Odoo 18
}
