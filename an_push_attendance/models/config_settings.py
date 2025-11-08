from odoo import models, fields, api
from odoo.exceptions import UserError


class AttendanceConfigSettings(models.Model):
    _name = 'attendance.config.settings'
    _description = 'Attendance Configuration Settings'
    _rec_name = 'employee_link_field'

    employee_link_field = fields.Selection([
        ('barcode', 'Badge ID'),
        ('fingerprint_no', 'Fingerprint No')
    ], string='Employee Link Field',
        default='fingerprint_no',
        required=True
    )

    # Default Policy Settings
    default_grace_period = fields.Float(
        string='Default Grace Period (minutes)',
        default=15.0,
        help='Default grace period in minutes if no policy is specified'
    )

    default_day_start_time = fields.Float(
        string='Default Day Start Time',
        default=21.0,
        help='Default hour when the working day starts (0-23)',
        widget='float_time'
    )

    default_policy_type = fields.Selection([
        ('flexible_period', 'Flexible Period'),
        ('first_check_time', 'First Check Time'),
        ('compute_with_calendar', 'Compute with Calendar'),
        ('device_status_code', 'Device Status Code')
    ], string='Default Policy Type',
        default='device_status_code',
        help='Default policy type for employees without specific policy'
    )

    @api.constrains('employee_link_field')
    def constarins_add(self):
        for r in self:
            if self.search([('id', '!=', r.id)]):
                raise UserError("Can't Add A New Record")

    @api.model
    def _get_employee_fields(self):
        employee_fields = self.env['hr.employee'].fields_get()
        field_list = [(field, employee_fields[field]['string'])
                      for field in employee_fields]
        return field_list

    @api.constrains('default_day_start_time')
    def _check_day_start_time(self):
        for record in self:
            if not 0 <= record.default_day_start_time <= 23:
                raise UserError("Day start time must be between 0 and 23")

    @api.constrains('default_grace_period')
    def _check_grace_period(self):
        for record in self:
            if record.default_grace_period < 0:
                raise UserError("Grace period cannot be negative")