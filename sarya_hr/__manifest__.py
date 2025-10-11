# -*- coding: utf-8 -*-
{
    'name': "sarya_hr",

    'summary': "Employee, Leave, Payroll Customizations.",

    'description': """
-Employee
-Time Off
-Payroll
-Attendance
    """,

    'author': "Pranav",
    'website': "https://www.sarya.ae",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'HR',
    'version': '17.1',

    # any module necessary for this one to work correctly
    'depends': ['portal',
                'hr',
                'l10n_in_hr_payroll',
                'hr_payroll_account',
                'hr_contract',
                'hr_holidays',
                'hr_work_entry_contract_enterprise',
                'web'],

    # always loaded
    'data': [
        'data/sequence.xml',
        'data/email_template.xml',
        'data/cron.xml',
        'data/employee_declaration_form_data.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/hr_employee.xml',
        'views/hr_contract.xml',
        'views/employee_doc_verify_view.xml',
        'views/employee_verify_portal_view.xml',
        'views/asset_category.xml',
        'views/assets.xml',
        'views/asset_history.xml',
        'views/bank_view.xml',
        'views/hr_leave_accrual_view.xml',
        'views/hr_leave_type.xml',
        'views/hr_grade.xml',
        'views/hr_inherit.xml',
        'views/hr_payslip.xml',
        'views/hr_leave.xml',
        'views/res_settings.xml',
        # 'views/time_off_dashboard.xml',
        'views/menu.xml',
        'reports/salary_register.xml',
        'views/employee_portal_templates.xml',
        'views/hr_leave_custom_form.xml',
        'views/action_render_templates.xml',
        'views/hr_tax_config_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'sarya_hr/static/src/js/employee_verify.js',
        ],
        'sarya_hr.webclient': [
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_backend_helpers'),

            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',

            'web/static/src/libs/fontawesome/css/font-awesome.css',
            'web/static/lib/odoo_ui_icons/*',
            'web/static/lib/select2/select2.css',
            'web/static/lib/select2-bootstrap-css/select2-bootstrap.css',
            'web/static/src/webclient/navbar/navbar.scss',
            'web/static/src/scss/animation.scss',
            'web/static/src/core/colorpicker/colorpicker.scss',
            'web/static/src/scss/mimetypes.scss',
            'web/static/src/scss/ui.scss',
            'web/static/src/legacy/scss/ui.scss',
            'web/static/src/views/fields/translation_dialog.scss',
            'web/static/src/scss/fontawesome_overridden.scss',

            'web/static/src/module_loader.js',
            'web/static/src/session.js',

            'web/static/lib/luxon/luxon.js',
            'web/static/lib/owl/owl.js',
            'web/static/lib/owl/odoo_module.js',
            'web/static/lib/jquery/jquery.js',
            'web/static/lib/popper/popper.js',
            'web/static/lib/bootstrap/js/dist/dom/data.js',
            'web/static/lib/bootstrap/js/dist/dom/event-handler.js',
            'web/static/lib/bootstrap/js/dist/dom/manipulator.js',
            'web/static/lib/bootstrap/js/dist/dom/selector-engine.js',
            'web/static/lib/bootstrap/js/dist/base-component.js',
            'web/static/lib/bootstrap/js/dist/alert.js',
            'web/static/lib/bootstrap/js/dist/button.js',
            'web/static/lib/bootstrap/js/dist/carousel.js',
            'web/static/lib/bootstrap/js/dist/collapse.js',
            'web/static/lib/bootstrap/js/dist/dropdown.js',
            'web/static/lib/bootstrap/js/dist/modal.js',
            'web/static/lib/bootstrap/js/dist/offcanvas.js',
            'web/static/lib/bootstrap/js/dist/tooltip.js',
            'web/static/lib/bootstrap/js/dist/popover.js',
            'web/static/lib/bootstrap/js/dist/scrollspy.js',
            'web/static/lib/bootstrap/js/dist/tab.js',
            'web/static/lib/bootstrap/js/dist/toast.js',
            'web/static/lib/select2/select2.js',
            'web/static/src/legacy/js/libs/bootstrap.js',
            'web/static/src/legacy/js/libs/jquery.js',
            ('include', 'web._assets_bootstrap_backend'),

            'base/static/src/css/modules.css',

            'web/static/src/core/utils/transitions.scss',
            'web/static/src/core/**/*',
            'web/static/src/model/**/*',
            'web/static/src/search/**/*',
            'web/static/src/webclient/icons.scss',  # variables required in list_controller.scss
            'web/static/src/views/**/*.js',
            'web/static/src/views/*.xml',
            'web/static/src/views/*.scss',
            'web/static/src/views/fields/**/*',
            'web/static/src/views/form/**/*',
            'web/static/src/views/kanban/**/*',
            'web/static/src/views/list/**/*',
            'web/static/src/views/view_button/**/*',
            'web/static/src/views/view_components/**/*',
            'web/static/src/views/view_dialogs/**/*',
            'web/static/src/views/widgets/**/*',
            'web/static/src/webclient/**/*',
            ('remove', 'web/static/src/webclient/clickbot/clickbot.js'),  # lazy loaded
            ('remove', 'web/static/src/views/form/button_box/*.scss'),
            ('remove', 'web/static/src/core/emoji_picker/emoji_data.js'),

            # remove the report code and whitelist only what's needed
            ('remove', 'web/static/src/webclient/actions/reports/**/*'),
            'web/static/src/webclient/actions/reports/*.js',
            'web/static/src/webclient/actions/reports/*.xml',

            'web/static/src/env.js',

            ('include', 'web_editor.assets_wysiwyg'),

            'web/static/src/legacy/scss/fields.scss',

            'base/static/src/scss/res_partner.scss',

            # Form style should be computed before
            'web/static/src/views/form/button_box/*.scss',

            'web_editor/static/src/js/editor/odoo-editor/src/base_style.scss',
            'web_editor/static/lib/vkbeautify/**/*',
            'web_editor/static/src/js/common/**/*',
            'web_editor/static/src/js/editor/odoo-editor/src/utils/utils.js',
            'web_editor/static/src/js/wysiwyg/fonts.js',

            'web_editor/static/src/components/**/*',
            'web_editor/static/src/scss/web_editor.common.scss',
            'web_editor/static/src/scss/web_editor.backend.scss',

            'web_editor/static/src/js/backend/**/*',
            'web_editor/static/src/xml/backend.xml',

            'mail/static/src/scss/variables/*.scss',
            'mail/static/src/views/web/form/form_renderer.scss',

            'sarya_hr/static/src/action_render/**/*',
            'web/static/src/start.js',
        ],
    },
}

