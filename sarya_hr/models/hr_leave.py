from odoo import fields, models, api,_
from datetime import datetime, timedelta, time
from math import ceil
from odoo.addons.resource.models.utils import float_to_time, HOURS_PER_DAY
from odoo.exceptions import ValidationError
from twilio.rest import Client
import json
import pytz
from pytz import timezone


class HRLeave(models.Model):
    _inherit = "hr.leave"

    manager_remark = fields.Char(string="Remark")

    def _get_duration(self, check_leave_type=True, resource_calendar=None):
        """
        This method is factored out into a separate method from
        _compute_duration so it can be hooked and called without necessarily
        modifying the fields and triggering more computes of fields that
        depend on number_of_hours or number_of_days.
        """
        self.ensure_one()
        company_resource_calendar = self.company_id.timeoff_resource_calendar_id or False
        if self.holiday_status_id and self.holiday_status_id.days_calculation == 'calendar' and company_resource_calendar:
            resource_calendar = company_resource_calendar
        else:
            resource_calendar = resource_calendar or self.resource_calendar_id

        if not self.date_from or not self.date_to or not resource_calendar:
            return (0, 0)
        hours, days = (0, 0)
        if self.employee_id:
            # We force the company in the domain as we are more than likely in a compute_sudo
            domain = [('time_type', '=', 'leave'),
                      ('company_id', 'in', self.env.companies.ids + self.env.context.get('allowed_company_ids', [])),
                      # When searching for resource leave intervals, we exclude the one that
                      # is related to the leave we're currently trying to compute for.
                      '|', ('holiday_id', '=', False), ('holiday_id', '!=', self.id)]
            if self.leave_type_request_unit == 'day' and check_leave_type:
                # list of tuples (day, hours)
                work_time_per_day_list = self.employee_id.list_work_time_per_day(self.date_from, self.date_to, calendar=resource_calendar, domain=domain)
                days = len(work_time_per_day_list)
                hours = sum(map(lambda t: t[1], work_time_per_day_list))
            else:
                work_days_data = self.employee_id._get_work_days_data_batch(self.date_from, self.date_to, domain=domain, calendar=resource_calendar)[self.employee_id.id]
                hours, days = work_days_data['hours'], work_days_data['days']
        else:
            today_hours = resource_calendar.get_work_hours_count(
                datetime.combine(self.date_from.date(), time.min),
                datetime.combine(self.date_from.date(), time.max),
                False)
            hours = resource_calendar.get_work_hours_count(self.date_from, self.date_to)
            days = hours / (today_hours or HOURS_PER_DAY)
        if self.leave_type_request_unit == 'day' and check_leave_type:
            days = ceil(days)
        return (days, hours)

    @api.constrains('number_of_days')
    def _check_medical_certificate(self):
        for leave in self:
            if (leave.leave_type_support_document and leave.number_of_days > 1 and not leave.attachment_ids):
                raise ValidationError(_("Medical Certificate is required for Sick Leaves more than 1 day."))

    def send_whatsapp_notification(self, button_url, message, to_numbers, content_sid):
        # Whatsapp message
        account_sid = self.env['ir.config_parameter'].sudo().get_param('twilio.account_sid', False)
        auth_token = self.env['ir.config_parameter'].sudo().get_param('twilio.auth_token', False)
        from_number = self.env['ir.config_parameter'].sudo().get_param('twilio.from', False)
        if from_number:
            from_number = "whatsapp:%s" % from_number

        for to_number in to_numbers:
            if account_sid and auth_token and from_number and to_number:
                to_number = to_number.replace(" ", '')
                to_number = "whatsapp:%s" % to_number
                content_variables = json.dumps({"1": message,
                                                "2": button_url})
                client = Client(account_sid, auth_token)
                try:
                    # Sending the message using Twilio API
                    twilio_message = client.messages.create(
                        from_=from_number,
                        content_sid=content_sid,
                        content_variables=content_variables,
                        to=to_number)
                except Exception as e:
                    pass

    def activity_update(self):
        res = super().activity_update()
        print('called', res)
        for holiday in self:
            to_numbers = []
            button_url = "#id=%s&cids=2&menu_id=634&action=935&model=hr.leave&view_type=form" % (str(self.id))
            if holiday.state not in ['validate', 'refuse']:
                user_ids = holiday.sudo()._get_responsible_for_approval() or False
                if not user_ids:
                    continue
                for user_id in user_ids:
                    manager_employee_id = user_id.employee_id
                    to_numbers.append("+971507893072")
                    if manager_employee_id.whatsapp_number:
                        to_numbers.append(manager_employee_id.whatsapp_number)
                    else:
                        # Fallback to mobile or work phone if whatsapp number is not available
                        to_numbers.append(manager_employee_id.mobile_phone and manager_employee_id.mobile_phone or manager_employee_id.work_phone)
                    if self.state == 'validate1' and self.employee_id.is_gm_notify_leave:
                        gm_mobile = self.env['ir.config_parameter'].sudo().get_param("gm_mobile", False)
                        if gm_mobile:
                            to_numbers.append(gm_mobile)
                    content_sid = 'HX5f8e0dbf691f97f0328170fe2c680376'
                    message = 'Employee: %s ,Approver: %s ,Leave Type:%s ,Duration:%s' % (holiday.employee_id.name, user_id.name, holiday.holiday_status_id.name, holiday.number_of_days_display)
                    if holiday.state == 'validate1' and self.manager_remark:
                        message = message + " ,Manager Remark:"+self.manager_remark
                    holiday.send_whatsapp_notification(button_url, message, to_numbers, content_sid)
            else:
                content_sid = 'HX9e7535b2cfdb97ccd86c49aaea223b42'
                to_numbers.append("+971507893072")
                status = "Approved"
                if holiday.state == 'refuse':
                    status = "Rejected"
                message = "for %s(%s days) is %s" %(holiday.holiday_status_id.name, holiday.number_of_days_display, status)
                if holiday.employee_id.whatsapp_number:
                    to_numbers.append(holiday.employee_id.whatsapp_number)
                else:
                    # Fallback to mobile or work phone if whatsapp number is not available
                    to_numbers.append(holiday.employee_id.mobile_phone and holiday.employee_id.mobile_phone or holiday.employee_id.work_phone)
                holiday.send_whatsapp_notification(button_url, message, to_numbers, content_sid)

        return res

    def _validate_leave_request(self):
        """ Validate time off requests (holiday_type='employee')
        by creating a calendar event and a resource time off. """
        holidays = self.filtered(lambda request: request.holiday_type == 'employee' and request.employee_id)
        holidays._create_resource_leave()
        meeting_holidays = holidays.filtered(lambda l: l.holiday_status_id.create_calendar_meeting)
        meetings = self.env['calendar.event']
        if meeting_holidays:
            meeting_values_for_user_id = meeting_holidays._prepare_holidays_meeting_values()
            Meeting = self.env['calendar.event']
            for user_id, meeting_values in meeting_values_for_user_id.items():
                meetings += Meeting.with_user(user_id or self.env.uid).with_context(
                                allowed_company_ids=[],
                                no_mail_to_attendees=True,
                                calendar_no_videocall=True,
                                active_model=self._name
                            ).sudo().create(meeting_values)
        Holiday = self.env['hr.leave']
        for meeting in meetings:
            Holiday.browse(meeting.res_id).meeting_id = meeting

        for holiday in holidays:
            user_tz = timezone(holiday.tz)
            utc_tz = pytz.utc.localize(holiday.date_from).astimezone(user_tz)
            notify_partner_ids = holiday.employee_id.user_id.partner_id.ids
            holiday.message_post(
                body=_(
                    'Your %(leave_type)s planned on %(date)s has been accepted',
                    leave_type=holiday.holiday_status_id.display_name,
                    date=utc_tz.replace(tzinfo=None)
                ),
                partner_ids=notify_partner_ids)
