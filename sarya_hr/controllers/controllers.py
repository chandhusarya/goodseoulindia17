# -*- coding: utf-8 -*-
from odoo import conf, http, _
from odoo.http import request
from odoo.exceptions import AccessError
import base64


class EmployeePortal(http.Controller):

    @http.route(['/employee/verify'], type='http', auth="public", website=True)
    def portal_employee_verify_templ(self, **kw):
        access_token = kw.get('access_token')
        verify_doc = request.env['employee.doc.verify'].sudo().search([
            ('verify_token', '=', access_token), ('state', '=', 'pending')])

        '''
        Get existing bank details
        '''
        bank = False
        acc_number, account_type, ifsc_code, bank_name, bank_branch = "", "", "", "", ""
        departments = request.env['hr.department'].sudo().search([('company_id', '=', verify_doc.employee_id.company_id.id)])
        designations = request.env['hr.job'].sudo().search([('company_id', '=', verify_doc.employee_id.company_id.id)])
        states = request.env['res.country.state'].sudo().search([])
        country = request.env['res.country'].sudo().search([])
        if verify_doc.employee_id and verify_doc.employee_id.work_contact_id:
            bank = request.env['res.partner.bank'].sudo().search([
                ('partner_id', '=', verify_doc.employee_id.work_contact_id.id)
            ])
            acc_number = bank and bank.acc_number
            account_type = bank and bank.account_type or ""
            bank_obj = bank and bank.bank_id
            if bank_obj:
                ifsc_code = bank_obj.bic or ""
                bank_name = bank_obj.name
                bank_branch = bank_obj.street or ""
        values = {'name': verify_doc.name,
                  'l10n_in_uan': verify_doc.l10n_in_uan,
                  'l10n_in_pan': verify_doc.l10n_in_pan,
                  'l10n_in_esic_number': verify_doc.l10n_in_esic_number,
                  'pf_number': verify_doc.pf_number,
                  'employee_name': verify_doc.employee_id.name,
                  'employee_id': verify_doc.employee_id.id,
                  'name_on_aadhaar': verify_doc.employee_id.name_on_aadhaar,
                  'aadhaar_number': verify_doc.employee_id.aadhaar_number,
                  'acc_number': acc_number,
                  'account_type': account_type,
                  'ifsc_code': ifsc_code,
                  'bank_name': bank_name,
                  'bank_branch': bank_branch,
                  'departments': departments,
                  'designations': designations,
                  'states': states,
                  'countries': country,
                  }
        return request.render('sarya_hr.portal_employee_verify_template', values)

    def create_documents(self, attached_file, employee, employee_folder, name, tag):
        Documents = request.env['documents.document'].sudo()
        existing_doc = Documents.search([
            ('name', '=', name),
            ('owner_id', '=', employee.user_id.id or request.env.user.id),
            ('folder_id', '=', employee_folder.id),
            # ('attachment_id.datas', '=', file_data),
        ], limit=1)
        if not existing_doc:
            Documents.create({
                'name': name,
                'datas': base64.b64encode(attached_file.read()),
                'res_model': 'hr.employee',
                'res_id': employee.id,
                'owner_id': employee.user_id.id or request.env.user.id,
                'partner_id': employee.work_contact_id.id,
                'mimetype': attached_file.content_type,
                'tag_ids': [(6, 0, [tag])] if tag else [(6, 0, [])],
                'folder_id': employee_folder.id,
            })
        return True

    @http.route(['/employee/verify/submit'], type='http', auth="public", website=True, csrf=False)
    def portal_employee_verify_submit_templ(self, **kw):
        kwargs = dict(request.params)
        values = {'message': 'Failed to update Data!', 'type': 'failed'}
        if kwargs['employee_id'] == '':
            return request.render('sarya_hr.portal_employee_verify_success_template', values)
        employee = request.env['hr.employee'].sudo().search([('id', '=', kwargs['employee_id'])])
        if len(employee) >= 1:
            data = {}
            bank_data = {}
            body_html = "Information updated by employee successfully:"
            # print("**********************************")
            # print("kwargs:", kwargs)
            # print("**********************************")
            if kwargs['l10n_in_uan'] != str(employee.l10n_in_uan):
                body_html += "UAN :" + str(kwargs['l10n_in_uan'])
                data['l10n_in_uan'] = kwargs['l10n_in_uan']
            if kwargs['l10n_in_pan'] != str(employee.l10n_in_pan):
                body_html += ", PAN Number :" + str(kwargs['l10n_in_pan'])
                data['l10n_in_pan'] = kwargs['l10n_in_pan']
            # if 'is_esic_applicable' in kwargs and kwargs['l10n_in_esic_number'] != str(employee.l10n_in_esic_number):
            #     body_html += ", ESIC :" + str(kwargs['l10n_in_esic_number'])
            #     data['l10n_in_esic_number'] = kwargs['l10n_in_esic_number']
            # if kwargs['pf_number'] != str(employee.pf_number):
            #     body_html += ", PF Number :" + str(kwargs['pf_number'])
            #     data['pf_number'] = kwargs['pf_number']

            # if 'is_esic_applicable' in kwargs and kwargs['is_esic_applicable'] != str(employee.pf_number):
            #     body_html += ", ESIC Applicable : Yes"
            #     data['is_esic_applicable'] = True
            # else:
            #     data['is_esic_applicable'] = False
            if 'is_pf_eligible' in kwargs and kwargs['is_pf_eligible'] != str(employee.is_pf_eligible):
                body_html += ", PF Eligible : Yes"
                data['is_pf_eligible'] = True
            else:
                data['is_pf_eligible'] = False
            # if 'is_excess_epf' in kwargs and kwargs['is_excess_epf'] != str(employee.is_excess_epf):
            #     body_html += ", Is employee eligible for excess EPF contribution :" + str(kwargs['is_excess_epf'])
            #     data['is_excess_epf'] = True
            # else:
            #     data['is_excess_epf'] = False
            # if 'is_existing_pf_member' in kwargs and kwargs['is_existing_pf_member'] != str(employee.is_existing_pf_member):
            #     body_html += ", Existing PF Member:" + str(kwargs['is_existing_pf_member'])
            #     data['is_existing_pf_member'] = True
            # else:
            #     data['is_existing_pf_member'] = False
            # if 'is_lwf_covered' in kwargs and kwargs['is_lwf_covered'] != str(employee.is_lwf_covered):
            #     body_html += ", Is LWF Covered: Yes"
            #     data['is_lwf_covered'] = True
            # else:
            #     data['is_lwf_covered'] = False
            if kwargs['name_on_aadhaar'] != str(employee.name_on_aadhaar):
                body_html += ", Name on Aadhar:" + str(kwargs['name_on_aadhaar'])
                data['name_on_aadhaar'] = kwargs['name_on_aadhaar']
            if kwargs['aadhaar_number'] != str(employee.aadhaar_number):
                body_html += ", Aadhar Number:" + str(kwargs['aadhaar_number'])
                data['aadhaar_number'] = kwargs['aadhaar_number']
            if kwargs['tax_regime'] != str(employee.tax_regime):
                body_html += ", TAX Regime:" + str(kwargs['tax_regime'])
                data['tax_regime'] = kwargs['tax_regime']
            if 'has_passport' in kwargs and kwargs['has_passport'] != str(employee.has_passport):
                body_html += ", Has Passport : Yes"
                data['has_passport'] = True
            else:
                data['has_passport'] = False
            if 'is_willing_to_relocate' in kwargs and kwargs['is_willing_to_relocate'] != str(employee.is_willing_to_relocate):
                body_html += ", Willing To Relocate : Yes"
                data['is_willing_to_relocate'] = True
            else:
                data['is_willing_to_relocate'] = False
            if 'is_any_disability' in kwargs and kwargs['is_any_disability'] != str(
                    employee.is_any_disability):
                body_html += ", Any Disability : Yes"
                data['is_any_disability'] = True
            else:
                data['is_any_disability'] = False

            if not employee.date_of_joining:
                data['date_of_joining'] = kwargs['date_of_joining']
            
            if not employee.birthday:
                data['birthday'] = kwargs['date_of_birth']

            if not employee.gender:
                data['gender'] = kwargs['gender']
            if not employee.marital and kwargs.get('marital_status'):
                data['marital'] = kwargs['marital_status']
            if not employee.fathers_name and kwargs.get('father_name'):
                data['fathers_name'] = kwargs['father_name']
            if not employee.husbands_name and kwargs.get('husband_name'):
                data['husbands_name'] = kwargs['husband_name']
            if not employee.mothers_name and kwargs.get('mother_name'):
                data['mothers_name'] = kwargs['mother_name']
            if not employee.private_phone and kwargs.get('contact_number'):
                data['private_phone'] = kwargs['contact_number']
            if not employee.emergency_phone and kwargs.get('emergency_number'):
                data['emergency_phone'] = kwargs['emergency_number']
            if not employee.private_street and kwargs.get('current_street'):
                data['private_street'] = kwargs['current_street']
            if not employee.private_city and kwargs.get('current_city'):
                data['private_city'] = kwargs['current_city']
            if not employee.private_state_id and kwargs.get('state_id'):
                # state = self.env['res.country.state'].search([('name', '=', kwargs['current_state'])], limit=1).id or False
                data['private_state_id'] = kwargs['state_id']
            if not employee.private_zip and kwargs.get('current_zip'):
                data['private_zip'] = kwargs['current_zip']
            if not employee.private_country_id and kwargs.get('country_id'):
                # country = self.env['res.country'].search([('name', '=', kwargs['current_country'])],
                #                                              limit=1).id or False
                data['private_state_id'] = kwargs['country_id']

            # street = kwargs.get('current_street')
            # city = kwargs.get('current_city')
            # state = kwargs.get('current_state')
            # zip_code = kwargs.get('current_zip')
            #
            # employee.write({
            #     'street': street,
            #     'city': city,
            #     'state_id': self.env['res.country.state'].search([('name', '=', state)], limit=1).id or False,
            #     'zip': zip_code,
            # })

            if not employee.bank_account_id:
                bank_data['acc_number'] = kwargs['acc_number']
                bank_data['account_type'] = kwargs['account_type']
                bank_data['ifsc_code'] = kwargs['ifsc_code']
                bank_data['bank_name'] = kwargs['bank_name']
                bank_data['bank_branch'] = kwargs['bank_branch']
            if not employee.department_id:
                department_id = kwargs.get('department_id')
                if department_id == 'other':
                    new_name = kwargs.get('other_department')
                    if new_name:
                        new_dept = request.env['hr.department'].sudo().create({
                            'name': new_name,
                            'company_id': request.env.company.id
                        })
                        department_id = new_dept.id
                data['department_id'] = int(department_id)
            if not employee.job_id:
                designation_id = kwargs.get('designation_id')
                if designation_id == 'other':
                    new_name = kwargs.get('other_designation')
                    if new_name:
                        new_dept = request.env['hr.job'].sudo().create({
                            'name': new_name,
                            'company_id': request.env.company.id
                        })
                        designation_id = new_dept.id
                data['job_id'] = int(designation_id)
            files = request.httprequest.files
            aadhaar_file = files.get('aadhaar_attachment')
            employee_under_hr_folder = request.env['documents.folder'].sudo().search([
                ('name', '=', 'Employee Documents')
            ], limit=1)
            if not employee_under_hr_folder:
                employee_under_hr_folder = request.env['documents.folder'].sudo().create({'name': 'Employee Documents'})
            employee_folder = request.env['documents.folder'].sudo().search([
                ('name', '=', employee.name),
                ('parent_folder_id', '=', employee_under_hr_folder.id)
            ], limit=1)
            if not employee_folder:
                employee_folder = request.env['documents.folder'].sudo().create({
                    'name': employee.name,
                    'parent_folder_id': employee_under_hr_folder.id,
                })
            if aadhaar_file:
                name = employee.name + '-' + 'Aadhar'
                tag = request.env['documents.tag'].sudo().search([
                ('name', '=', 'Aadhar')
                ], limit=1).id
                self.create_documents(aadhaar_file, employee, employee_folder, name, tag)

            cheque_file = files.get('cheque_attachment')
            if cheque_file:
                name = employee.name + '-' + 'Cheque'
                self.create_documents(cheque_file, employee, employee_folder, name, tag=False)
            pan_file = files.get('pan_attachment')
            if pan_file:
                name = employee.name + '-' + 'PAN'
                tag = request.env['documents.tag'].sudo().search([
                    ('name', '=', 'PAN')
                ], limit=1).id
                self.create_documents(pan_file, employee, employee_folder, name, tag)
            resume_file = files.get('resume_attachment')
            if resume_file:
                name = employee.name + '-' + 'Resume'
                self.create_documents(resume_file, employee, employee_folder, name, tag=False)
            previous_offer_letter_file_1 = files.get('previous_offer_letter_attachment_1')
            if previous_offer_letter_file_1:
                name = employee.name + '-' + 'Previous Offer Letter 1'
                self.create_documents(previous_offer_letter_file_1, employee, employee_folder, name, tag=False)
            previous_offer_letter_file_2 = files.get('previous_offer_letter_attachment_2')
            if previous_offer_letter_file_2:
                name = employee.name + '-' + 'Previous Offer Letter 2'
                self.create_documents(previous_offer_letter_file_2, employee, employee_folder, name, tag=False)
            previous_offer_letter_file_3 = files.get('previous_offer_letter_attachment_3')
            if previous_offer_letter_file_3:
                name = employee.name + '-' + 'Previous Offer Letter 3'
                self.create_documents(previous_offer_letter_file_3, employee, employee_folder, name, tag=False)
            three_month_pay_slip_file = files.get('pay_slip_1')
            if three_month_pay_slip_file:
                name = employee.name + '-' + 'Pay Slip 1'
                self.create_documents(three_month_pay_slip_file, employee, employee_folder, name, tag=False)
            pay_slip_file_2 = files.get('pay_slip_2')
            if pay_slip_file_2:
                name = employee.name + '-' + 'Pay Slip 2'
                self.create_documents(pay_slip_file_2, employee, employee_folder, name, tag=False)
            pay_slip_file_3 = files.get('pay_slip_3')
            if pay_slip_file_3:
                name = employee.name + '-' + 'Pay Slip 3'
                self.create_documents(pay_slip_file_3, employee, employee_folder, name, tag=False)
            passport_size_photo = files.get('passport_size_photo')
            if passport_size_photo:
                name = employee.name + '-' + 'Passport Size Photo'
                self.create_documents(passport_size_photo, employee, employee_folder, name, tag=False)
            passport_copy = files.get('passport_copy')
            if passport_copy:
                name = employee.name + '-' + 'Passport Copy'
                self.create_documents(passport_copy, employee, employee_folder, name, tag=False)
            graduation_certificate = files.get('graduation_certificate')
            if graduation_certificate:
                name = employee.name + '-' + 'Graduation Certificate'
                self.create_documents(graduation_certificate, employee, employee_folder, name, tag=False)
            graduation_marksheet = files.get('graduation_marksheet')
            if graduation_marksheet:
                name = employee.name + '-' + 'Graduation Marksheet'
                self.create_documents(graduation_marksheet, employee, employee_folder, name, tag=False)
            hsc_certificate = files.get('hsc_certificate')
            if hsc_certificate:
                name = employee.name + '-' + 'HSC Certificate'
                self.create_documents(hsc_certificate, employee, employee_folder, name, tag=False)
            ssc_certificate = files.get('ssc_certificate')
            if ssc_certificate:
                name = employee.name + '-' + 'SSC Certificate'
                self.create_documents(ssc_certificate, employee, employee_folder, name, tag=False)
            post_graduation = files.get('post_graduation')
            if post_graduation:
                name = employee.name + '-' + 'Post Graduation'
                self.create_documents(post_graduation, employee, employee_folder, name, tag=False)
            relieving_letter = files.get('relieving_letter')
            if relieving_letter:
                name = employee.name + '-' + 'Relieving Letter'
                self.create_documents(relieving_letter, employee, employee_folder, name, tag=False)
            relieving_letter = files.get('relieving_letter')
            if relieving_letter:
                name = employee.name + '-' + 'Relieving Letter'
                self.create_documents(relieving_letter, employee, employee_folder, name, tag=False)
            response_message = employee.sudo().employee_portal_update(data, bank_data)
            employee.message_post(body=_(body_html))
            values = {'message': response_message, 'type': 'success'}
        return request.render('sarya_hr.portal_employee_verify_success_template', values)



class PortalLeaveRequest(http.Controller):


    @http.route(['/my/leave/request'], type='http', auth='user', website=True)
    def portal_leave_request_render_backend_form(self, **kwargs):
        employee = request.env['hr.employee'].sudo().search([('user_id', '=', request.uid)], limit=1)
        if not employee:
            raise AccessError("No employee linked to this user.")
        get_leave_action = employee.sudo().action_open_leave_form()
        session_info = request.env['ir.http'].session_info()
        user_context = dict(request.env.context) if request.session.uid else {}
        mods = conf.server_wide_modules or []
        if request.env.lang:
            lang = request.env.lang
            session_info['user_context']['lang'] = lang
            user_context['lang'] = lang
        lang = user_context.get("lang")
        translation_hash = request.env['ir.http'].get_web_translations_hash(mods, lang)
        cache_hashes = {
            "translations": translation_hash,
        }
        session_info.update(
            cache_hashes=cache_hashes,
            action_name=get_leave_action,
            user_companies={
                'current_company': employee.company_id.id,
                'allowed_companies': {
                    employee.company_id.id: {
                        'id': employee.company_id.id,
                        'name': employee.company_id.name,
                    },
                },
            },
        )
        session_info['open_task_action'] = get_leave_action
        return request.render(
            'sarya_hr.action_render_embed',
            {'session_info': session_info},
        )

    @http.route(['/my/leaves/history'], type='http', auth='user', website=True)
    def portal_leaves_history_render_backend_tree(self, **kwargs):
        employee = request.env['hr.employee'].sudo().search([('user_id', '=', request.uid)], limit=1)
        if not employee:
            raise AccessError("No employee linked to this user.")
        get_leave_action = employee.sudo().action_open_leave_tree()
        session_info = request.env['ir.http'].session_info()
        user_context = dict(request.env.context) if request.session.uid else {}
        mods = conf.server_wide_modules or []
        if request.env.lang:
            lang = request.env.lang
            session_info['user_context']['lang'] = lang
            user_context['lang'] = lang
        lang = user_context.get("lang")
        translation_hash = request.env['ir.http'].get_web_translations_hash(mods, lang)
        cache_hashes = {
            "translations": translation_hash,
        }
        session_info.update(
            cache_hashes=cache_hashes,
            action_name=get_leave_action,
            user_companies={
                'current_company': employee.company_id.id,
                'allowed_companies': {
                    employee.company_id.id: {
                        'id': employee.company_id.id,
                        'name': employee.company_id.name,
                    },
                },
            },
        )
        session_info['open_task_action'] = get_leave_action
        return request.render(
            'sarya_hr.action_render_embed',
            {'session_info': session_info},
        )




