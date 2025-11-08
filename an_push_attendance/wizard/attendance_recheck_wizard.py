from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import calendar

class AttendanceRecheckWizard(models.TransientModel):
    _name = 'attendance.recheck.wizard'
    _description = 'Attendance Recheck Wizard'

    # Processing Options
    do_recheck = fields.Boolean(string='Recheck Attendance', default=True,
                              help='Recompute check-in/out status for attendance records')
    do_process = fields.Boolean(string='Process to Attendance Process', default=True,
                              help='Create attendance process records')
    do_hr_attendance = fields.Boolean(string='Process to HR Attendance', default=True,
                              help='Create HR attendance records')

    # Selection Type
    selection_type = fields.Selection([
        ('employee', 'Employees'),
        ('department', 'Department'),
        ('all', 'All Employees')
    ], string='Selection Type', required=True, default='employee')

    # Employee Fields
    employee_ids = fields.Many2many('hr.employee', string='Employees')
    department_id = fields.Many2one('hr.department', string='Department')

    # Date Fields
    date_selection = fields.Selection([
        ('month', 'Month'),
        ('custom', 'Custom Period')
    ], string='Date Selection', required=True, default='month')

    # Month Selection
    year = fields.Integer(string='Year', default=lambda self: fields.Date.today().year)
    month = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December')
    ], string='Month', default=lambda self: str(fields.Date.today().month))

    # Custom Period
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')

    @api.onchange('selection_type')
    def _onchange_selection_type(self):
        self.employee_ids = False
        self.department_id = False

    @api.onchange('date_selection')
    def _onchange_date_selection(self):
        self.start_date = False
        self.end_date = False
        if self.date_selection == 'month':
            self._update_dates_from_month()

    @api.onchange('month', 'year')
    def _onchange_month_year(self):
        if self.date_selection == 'month':
            self._update_dates_from_month()

    def _update_dates_from_month(self):
        if self.month and self.year:
            month_int = int(self.month)
            # Get first day of selected month
            first_day = date(self.year, month_int, 1)
            # Get last day of selected month
            last_day = first_day + relativedelta(months=1, days=-1)
            
            self.start_date = first_day
            self.end_date = last_day

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for wizard in self:
            if wizard.start_date and wizard.end_date and wizard.start_date > wizard.end_date:
                raise ValidationError('Start date must be before end date')

    def _get_employees(self):
        if self.selection_type == 'employee':
            return self.employee_ids
        elif self.selection_type == 'department':
            if not self.department_id:
                raise ValidationError('Please select a department')
            return self.env['hr.employee'].search([('department_id', '=', self.department_id.id)])
        else:  # all employees
            return self.env['hr.employee'].search([('active', '=', True)])

    def action_recheck_period(self):
        self.ensure_one()

        if not self.start_date or not self.end_date:
            raise ValidationError('Please select valid dates')

        if not any([self.do_recheck, self.do_process, self.do_hr_attendance]):
            raise ValidationError('Please select at least one processing option')

        employees = self._get_employees()
        if not employees:
            raise ValidationError('No employees selected')

        total_records = 0
        errors = []

        for employee in employees:
            try:
                # Call the recheck_period method for each employee
                records_count = self.env['attendance.record'].recheck_period(
                    employee.id,
                    self.start_date,
                    self.end_date,
                    self.do_recheck,
                    self.do_process,
                    self.do_hr_attendance
                )
                total_records += records_count
                
            except Exception as e:
                errors.append(f"Error processing {employee.name}: {str(e)}")
                continue

        # Prepare result message
        if errors:
            message = f"Processed {total_records} records with some errors:\n" + "\n".join(errors)
            message_type = 'warning'
        else:
            message = f"Successfully processed {total_records} records for {len(employees)} employees"
            message_type = 'success'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Process Complete',
                'message': message,
                'type': message_type,
                'sticky': bool(errors),
            }
        } 