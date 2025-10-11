from odoo import fields, models, api, _
from odoo.exceptions import UserError
import random, string
from dateutil.relativedelta import relativedelta
from datetime import date
from markupsafe import Markup
from odoo.tools.date_utils import get_timedelta
from odoo.addons.resource.models.utils import HOURS_PER_DAY


class Employee(models.Model):
    _inherit = 'hr.employee'

    pf_number = fields.Char('PF Number', tracking=True)
    is_esic_applicable = fields.Boolean(
        string='ESIC Applicable', tracking=True)
    verify_token = fields.Char(
        string='Verify Token')
    employee_verified = fields.Boolean('Employee Verified', default=False)
    employee_verification_mail_sent = fields.Boolean('Employee Verification Email Sent', default=False)
    probation_period = fields.Integer(string='Probation Period(Months)')
    probation_completion_date = fields.Date(compute='_compute_probation_completion')
    asset_count = fields.Integer(compute='_get_asset_count')
    is_pf_eligible = fields.Boolean(string='Is employee eligible for PF?', tracking=True)
    is_excess_epf = fields.Boolean(string='Is employee eligible for excess EPF contribution?', tracking=True)
    is_existing_pf_member = fields.Boolean(string='Is existing member of PF?', tracking=True)
    is_lwf_covered = fields.Boolean(string='Is employee covered under LWF?', tracking=True)
    name_on_aadhaar = fields.Char(string="Name (As on Aadhaar Card)", tracking=True)
    aadhaar_number = fields.Char(string="Aadhaar Card Number", tracking=True)
    tax_regime = fields.Selection(
        string='Tax Regime',
        selection=[('old', 'Old'),
                   ('new', 'New'), ], default='new', tracking=True)
    outstation_travel = fields.Boolean(
        string='Outstation Travel', default=False)
    analytic_account_ids = fields.Many2many(
        comodel_name='account.analytic.account',
        string='Work Regions')
    grade_id = fields.Many2one('hr.grade', related='job_id.grade_id')


    whatsapp_number = fields.Char(string='WhatsApp Number', tracking=True, help="WhatsApp number of the employee. This is used to send notifications via WhatsApp."
                                  " If not provided, the mobile number will be used for WhatsApp notifications.")
    is_gm_notify_leave = fields.Boolean(string='GM Notify')
    leaves_allocated = fields.Boolean(string='Leaves Allocated')
    date_of_joining = fields.Date(
        string='Date of Joining'
    )
    fathers_name = fields.Char(
        string='Fathers Name'
    )
    mothers_name = fields.Char(
        string='Mother Name'
    )
    husbands_name = fields.Char(
        string='Husband Name'
    )
    has_passport = fields.Boolean(string='Has Passport?', tracking=True)
    is_willing_to_relocate = fields.Boolean(string='Willing To Relocate?', tracking=True)
    is_any_disability = fields.Boolean(string='Any Disability?', tracking=True)


    def _get_asset_count(self):
        for rec in self:
            ast = self.env['asset.history'].search([('employee_id', '=', rec.id)])
            rec.asset_count = len(ast)

    def _compute_probation_completion(self):
        for employee in self:
            if employee.probation_period > 0:
                employee.probation_completion_date = employee.first_contract_date + relativedelta(months=employee.probation_period)
            else:
                employee.probation_completion_date = False

    def send_for_verification(self):
        if not self.private_email:
            raise UserError(_('Add employee private email address before you send for verification.'))
        doc_ver_obj = self.env['employee.doc.verify']
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        rec = doc_ver_obj.create({
            'employee_id': self.id,
            'l10n_in_uan': self.l10n_in_uan,
            'l10n_in_pan': self.l10n_in_pan,
            'l10n_in_esic_number': self.l10n_in_esic_number,
            'pf_number': self.pf_number,
            'verify_token': token,
        })
        # email_cc = ""
        # if self.parent_id and self.parent_id.work_email:
        #     email_cc = self.parent_id.work_email
        mail_content = {
            'author_id': self.env.user.partner_id.id,
            'email_to': self.private_email,
        }
        self.employee_verified = False
        self.employee_verification_mail_sent = True
        self.message_post(body=_("Email sent for verification."))
        mail_template = self.env.ref('sarya_hr.employee_verify_mail_template')
        mail_template.sudo().send_mail(rec.id, force_send=True, email_values=mail_content)

    def employee_portal_update(self, values, bank_values):
        try:
            if values or bank_values:
                bank = False
                if 'ifsc_code' in bank_values and bank_values['ifsc_code'] != "":
                    bank_obj = self.env['res.bank'].sudo()
                    bank = bank_obj.search([('bic', '=', bank_values['ifsc_code'])], limit=1)
                    if not bank:
                        bank = bank_obj.create({
                            'name': bank_values['bank_name'],
                            'bic': bank_values['ifsc_code'],
                            'street': bank_values['bank_branch']
                        })
                        # print('Bank : ', bank)
                    partner_bank = self.env['res.partner.bank'].sudo().create({
                        'partner_id': self.work_contact_id and self.work_contact_id.id,
                        'bank_id': bank.id,
                        'acc_number': bank_values['acc_number'],
                        'account_type': bank_values['account_type'],
                        'company_id': self.company_id.id,
                    })
                    values['bank_account_id'] = partner_bank.id

                values['employee_verified'] = True
                self.write(values)
                # self.generate_verified_document_bundle()
                requests = self.env['employee.doc.verify'].search([('employee_id', '=', self.id), ('state', '=', 'pending')])
                requests.write({'state': 'verified'})
                return 'Employee data successfully updated.'
            else:
                return 'Nothing to update.'
        except Exception as e:
            message = (_(u'Unknown error during import:') + u' %s: %s' % (type(e), e))
            # print('Message:', message)
            return message

    def _autonotify_probation_end(self):
        employees = self.env['hr.employee'].search([('active', '=', True),
                                                    ('first_contract_date', '!=', False),
                                                    '|', ('probation_completion_date', '!=', False),  ('probation_completion_date', '=', date.today())])
        probation_employee = ''
        for employee in employees:
            if employee.probation_completion_date:
                if employee.probation_completion_date.strftime('%Y-%m-%d') == date.today().strftime('%Y-%m-%d'):
                    probation_employee +=  '<tr><td> ' + str(employee.name) + ' </td><td> ' + employee.first_contract_date.strftime('%d-%b-%Y') + ' </td><td> ' + str(employee.probation_period) + ' months </td></tr>'
        if not probation_employee:
            return
        mail_content = "  Hello,<br/>Probation Period has been completed today for below employee(s)."
        mail_content += "<br/><br/><table><thead><th style='width:50%'>Employee</th><th style='width:30%'>Joining Date</th><th style='width:20%'>Probation Period</th></thead><tbody>"
        mail_content += probation_employee
        mail_content += "</tbody></table>"
        main_content = {
            'subject': _('Probation Period Completion '),
            'body_html': mail_content,
            'email_to': 'hr@sarya.ae',
        }
        self.env['mail.mail'].create(main_content).send()

    def action_open_asset(self):
        return {
            'name': 'Asset Log',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'asset.history',
            'context': {'default_employee_id': self.id},
            'domain': [('employee_id', '=', self.id)],
            'target': 'current'
        }

    def _get_timeoff_data(self, date=None):
        res = super()._get_timeoff_data(date=date)

        # Prepare utilised data (label, value, id)
        utilised_data = []
        for holiday_status in self.env['hr.leave.type'].search([]):
            domain = [
                ('employee_id', 'in', self.ids),
                ('state', '=', 'validate'),
                ('holiday_status_id', '=', holiday_status.id),
            ]
            if date:
                domain += [('request_date_to', '<=', date)]

            total_days = sum(self.env['hr.leave'].search(domain).mapped('number_of_days'))
            if total_days:
                utilised_data.append([holiday_status.name, total_days, holiday_status.id])

        res['utilised_holidays'] = utilised_data
        return res

    def create_leave_for_particular_employee(self):
        if not self.first_contract_date or not self.sudo().contract_ids:
            raise UserError(_("Please Add the contract for employee first"))
        accrual_plans = self.env['hr.leave.accrual.plan'].search([])
        if accrual_plans:
            for rec in accrual_plans:
                # work_entry_type = self.env['hr.work.entry.type'].search([('code', 'in', ['LEAVE120', 'LEAVE130'])])
                # leave_types = self.env['hr.leave.type'].search([('work_entry_type_id', 'in', work_entry_type.ids)])
                # leave_types = [entry_type for entry_type in self.env['hr.leave.type'].search([('work_entry_type_id')])]
                # for le_type in leave_types:
                allocate_vals = {
                    'name': rec.name + 'Allocation',
                    'holiday_status_id': rec.time_off_type_id.id,
                    'allocation_type': 'accrual',
                    'date_from': self.first_contract_date,
                    'holiday_type': 'employee',
                    'accrual_plan_id': rec.id,
                    'employee_id': self.id,
                }
                leave_allocation_id = self.env['hr.leave.allocation'].sudo().create(allocate_vals)
                leave_allocation_id._onchange_date_from()
                leave_allocation_id.action_validate()
                message = Markup("<p>%(allocation_name)s<p>") % {
                    'allocation_name': leave_allocation_id._get_html_link(),
                }
                self.message_post(body=message)
                self.leaves_allocated = True

    def action_open_leave(self):
        return {
            'view_mode': 'form',
            'res_model': 'hr.leave',
            'type': 'ir.actions.act_window',
            'target': 'main',
            'context': {
            'default_request_date_from': False,
            'default_request_date_to': False,
        }
        }

    def action_open_leave_form(self):
        action = self.action_open_leave()
        print('action', action)
        action['views'] = [[self.env.ref('sarya_hr.hr_leave_view_custom_sarya_form').id, 'form']]
        print('action_after', action)
        return action

    def action_open_leave_tree(self):
        action = {
            'view_mode': 'tree',
            'res_model': 'hr.leave',
            'type': 'ir.actions.act_window',
            'domain': [('employee_id', '=', self.id)],
            'context': {'create': False}
        }
        action['views'] = [[self.env.ref('sarya_hr.hr_leave_view_sarya_custom_tree').id, 'tree']]
        action['display_name'] = 'Time Off'
        return action


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    pf_number = fields.Char('PF Number', tracking=True)
    is_esic_applicable = fields.Boolean(
        string='ESIC Applicable', tracking=True)
    verify_token = fields.Char(
        string='Verify Token')
    employee_verified = fields.Boolean('Employee Verified', default=False)
    employee_verification_mail_sent = fields.Boolean('Employee Verification Email Sent', default=False)
    probation_period = fields.Integer(string='Probation Period(Months)')
    probation_completion_date = fields.Date(compute='_compute_probation_completion')
    asset_count = fields.Integer(compute='_get_asset_count')
    is_pf_eligible = fields.Boolean(string='Is employee eligible for PF?', tracking=True)
    is_excess_epf = fields.Boolean(string='Is employee eligible for excess EPF contribution?', tracking=True)
    is_existing_pf_member = fields.Boolean(string='Is existing member of PF?', tracking=True)
    is_lwf_covered = fields.Boolean(string='Is employee covered under LWF?', tracking=True)
    name_on_aadhaar = fields.Char(string="Name (As on Aadhaar Card)", tracking=True)
    aadhaar_number = fields.Char(string="Aadhaar Card Number", tracking=True)
    tax_regime = fields.Selection(
        string='Tax Regime',
        selection=[('old', 'Old'),
                   ('new', 'New'), ], default='new', tracking=True)
    outstation_travel = fields.Boolean(
        string='Outstation Travel', default=False)

    whatsapp_number = fields.Char(string='WhatsApp Number', tracking=True,
                                 help="WhatsApp number of the employee. This is used to send notifications via WhatsApp."
                                      " If not provided, the mobile number will be used for WhatsApp notifications.")
    is_gm_notify_leave = fields.Boolean(string='GM Notify')
    leaves_allocated = fields.Boolean(string='Leaves Allocated')
    date_of_joining = fields.Date(
        string='Date of Joining'
    )
    fathers_name = fields.Char(
        string='Fathers Name'
    )
    mothers_name = fields.Char(
        string='Mother Name'
    )
    husbands_name = fields.Char(
        string='Husband Name'
    )
    has_passport = fields.Boolean(string='Has Passport?', tracking=True)
    is_willing_to_relocate = fields.Boolean(string='Willing To Relocate?', tracking=True)
    is_any_disability = fields.Boolean(string='Any Disability?', tracking=True)
    # all_documents_file = fields.Binary("Verified Documents (PDF)")
    # all_documents_filename = fields.Char("Filename")

    # @api.model
    # def _get_fields(self):
    #     # Get the default fields from the original method
    #     fields = super(HrEmployeePublic, self)._get_fields()
    #     # Add your custom field(s) if needed
    #     print("fields>>>>>>>>>>>>>>", fields)
    #     fields = fields + ("emp.pf_number,emp.is_esic_applicable,emp.verify_token,emp.employee_verified,emp.employee_verification_mail_sent,"
    #                        "emp.probation_period,emp.probation_completion_date,emp.asset_count,emp.is_pf_eligible,emp.is_excess_epf,"
    #                        "emp.is_existing_pf_member,emp.is_lwf_covered,emp.name_on_aadhaar,emp.aadhaar_number,emp.tax_regime,emp.outstation_travel")
    #     return fields

    @api.model
    def _get_fields(self):
        return ','.join('emp.%s' % name for name, field in self._fields.items() if
                        field.store and field.type not in ['many2many', 'one2many'])


class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    @api.onchange('date_from', 'accrual_plan_id', 'date_to', 'employee_id')
    def _onchange_date_from(self):
        if not self.employee_id and self.allocation_type == 'accrual':
            self.number_of_days = 0
        if not self.date_from or self.allocation_type != 'accrual' or self.state == 'validate' or not self.accrual_plan_id\
            or not self.employee_id:
            return
        self.lastcall = self.date_from
        self.nextcall = False
        self.number_of_days_display = 0.0
        self.number_of_hours_display = 0.0
        self.number_of_days = 0.0
        date_to = min(self.date_to, date.today()) if self.date_to else False
        self._process_accrual_plans(date_to)


    def _process_accrual_plans(self, date_to=False, force_period=False, log=True):
        """
        This method is part of the cron's process.
        The goal of this method is to retroactively apply accrual plan levels and progress from nextcall to date_to or today.
        If force_period is set, the accrual will run until date_to in a prorated way (used for end of year accrual actions).
        """
        print('entered')
        date_to = date_to or fields.Date.today()
        already_accrued = {allocation.id: allocation.already_accrued or (allocation.number_of_days != 0 and allocation.accrual_plan_id.accrued_gain_time == 'start') for allocation in self}
        first_allocation = _("""This allocation have already ran once, any modification won't be effective to the days allocated to the employee. If you need to change the configuration of the allocation, delete and create a new one.""")
        for allocation in self:
            level_ids = allocation.accrual_plan_id.level_ids.sorted('sequence')
            if not level_ids:
                continue
            # "cache" leaves taken, as it gets recomputed every time allocation.number_of_days is assigned to. Without this,
            # every loop will take 1+ second. It can be removed if computes don't chain in a way to always reassign accrual plan
            # even if the value doesn't change. This is the best performance atm.
            first_level = level_ids[0]
            first_level_start_date = allocation.date_from + get_timedelta(first_level.start_count, first_level.start_type)
            leaves_taken = allocation.leaves_taken if allocation.holiday_status_id.request_unit in ["day", "half_day"] else allocation.leaves_taken / (allocation.employee_id.sudo().resource_id.calendar_id.hours_per_day or HOURS_PER_DAY)
            allocation.already_accrued = already_accrued[allocation.id]
            # first time the plan is run, initialize nextcall and take carryover / level transition into account
            if not allocation.nextcall:
                # Accrual plan is not configured properly or has not started
                if date_to < first_level_start_date:
                    continue
                allocation.lastcall = max(allocation.lastcall, first_level_start_date)
                allocation.nextcall = first_level._get_next_date(allocation.lastcall)
                # adjust nextcall for carryover
                carryover_date = allocation._get_carryover_date(allocation.nextcall)
                allocation.nextcall = min(carryover_date, allocation.nextcall)
                # adjust nextcall for level_transition
                if len(level_ids) > 1:
                    second_level_start_date = allocation.date_from + get_timedelta(level_ids[1].start_count, level_ids[1].start_type)
                    allocation.nextcall = min(second_level_start_date, allocation.nextcall)
                if log:
                    allocation._message_log(body=first_allocation)
            (current_level, current_level_idx) = (False, 0)
            current_level_maximum_leave = 0.0
            # all subsequent runs, at every loop:
            # get current level and normal period boundaries, then set nextcall, adjusted for level transition and carryover
            # add days, trimmed if there is a maximum_leave
            while allocation.nextcall <= date_to:
                (current_level, current_level_idx) = allocation._get_current_accrual_plan_level_id(allocation.nextcall)
                if not current_level:
                    break
                if current_level.cap_accrued_time:
                    current_level_maximum_leave = current_level.maximum_leave if current_level.added_value_type == "day" else current_level.maximum_leave / (allocation.employee_id.sudo().resource_id.calendar_id.hours_per_day or HOURS_PER_DAY)
                nextcall = current_level._get_next_date(allocation.nextcall)
                # Since _get_previous_date returns the given date if it corresponds to a call date
                # this will always return lastcall except possibly on the first call
                # this is used to prorate the first number of days given to the employee
                period_start = current_level._get_previous_date(allocation.lastcall)
                period_end = current_level._get_next_date(allocation.lastcall)
                # There are 2 cases where nextcall could be closer than the normal period:
                # 1. Passing from one level to another, if mode is set to 'immediately'
                if current_level_idx < (len(level_ids) - 1) and allocation.accrual_plan_id.transition_mode == 'immediately':
                    next_level = level_ids[current_level_idx + 1]
                    current_level_last_date = allocation.date_from + get_timedelta(next_level.start_count, next_level.start_type)
                    if allocation.nextcall != current_level_last_date:
                        nextcall = min(nextcall, current_level_last_date)
                # 2. On carry-over date
                carryover_date = allocation._get_carryover_date(allocation.nextcall)
                if allocation.nextcall < carryover_date < nextcall:
                    nextcall = min(nextcall, carryover_date)
                if not allocation.already_accrued:
                    allocation._add_days_to_allocation(current_level, current_level_maximum_leave, leaves_taken, period_start, period_end)
                # if it's the carry-over date, adjust days using current level's carry-over policy, then continue
                if allocation.nextcall == carryover_date:
                    if current_level.action_with_unused_accruals in ['lost', 'maximum']:
                        allocated_days_left = allocation.number_of_days - leaves_taken
                        allocation_max_days = 0 # default if unused_accrual are lost
                        if current_level.action_with_unused_accruals == 'maximum':
                            postpone_max_days = current_level.postpone_max_days if current_level.added_value_type == 'day' else current_level.postpone_max_days / (allocation.employee_id.sudo().resource_id.calendar_id.hours_per_day or HOURS_PER_DAY)
                            allocation_max_days = min(postpone_max_days, allocated_days_left)
                        allocation.number_of_days = min(allocation.number_of_days, allocation_max_days) + leaves_taken

                allocation.lastcall = allocation.nextcall
                allocation.nextcall = nextcall
                allocation.already_accrued = False
                if force_period and allocation.nextcall > date_to:
                    allocation.nextcall = date_to
                    force_period = False

            # if plan.accrued_gain_time == 'start', process next period and set flag 'already_accrued', this will skip adding days
            # once, preventing double allocation.
            if allocation.accrual_plan_id.accrued_gain_time == 'start':
                # check that we are at the start of a period, not on a carry-over or level transition date
                level_start = {level._get_level_transition_date(allocation.date_from): level for level in allocation.accrual_plan_id.level_ids}
                current_level = level_start.get(allocation.lastcall) or current_level or allocation.accrual_plan_id.level_ids[0]
                period_start = current_level._get_previous_date(allocation.lastcall)
                if current_level.cap_accrued_time:
                    current_level_maximum_leave = current_level.maximum_leave if current_level.added_value_type == "day" else current_level.maximum_leave / (allocation.employee_id.sudo().resource_id.calendar_id.hours_per_day or HOURS_PER_DAY)
                allocation._add_days_to_allocation(current_level, current_level_maximum_leave, leaves_taken, period_start, allocation.nextcall)
                allocation.already_accrued = True

class HrLeaveMandatoryDay(models.Model):
    _inherit = 'hr.leave.accrual.level'

    def _get_level_transition_date(self, allocation_start):
        if self.start_type == 'day':
            return allocation_start + relativedelta(days=self.start_count)
        if self.start_type == 'month':
            return allocation_start + relativedelta(months=self.start_count)
        if self.start_type == 'year':
            return allocation_start + relativedelta(years=self.start_count)



class HrLeaveMandatoryDay(models.Model):
    _inherit = 'hr.leave.mandatory.day'

class ResourceCalendarAttendance(models.Model):
    _inherit = 'resource.calendar.attendance'


class ResourceCalendarLeaves(models.Model):
    _inherit = 'resource.calendar.leaves'

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

class MailActivity(models.Model):
    _inherit = 'mail.activity'

class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'