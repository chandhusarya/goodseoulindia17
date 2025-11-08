from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime


class FPStatusPolicy(models.Model):
    _name = 'fp.status.policy'
    _description = 'Fingerprint Status Policy'
    _order = 'start_date desc, id desc'  # Order by date desc so newest first

    name = fields.Char(string='Policy Name', required=True)
    employee_ids = fields.Many2many('hr.employee', 'employee_policy_rel', 'policy_id', 'employee_id',
                                    string='Employees')
    active = fields.Boolean(default=True)

    # Add date fields
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date')
    is_default = fields.Boolean(string='Is Default Policy', compute='_compute_is_default', store=True)

    policy_type = fields.Selection([
        ('flexible_period', 'Flexible Period'),
        ('first_check_time', 'First Check Time'),
        ('compute_with_calendar', 'Compute with Calendar'),
        ('device_status_code', 'Device Status Code')
    ], string='Policy Type', required=True, default='flexible_period',
       help="Flexible Period: Alternates check-in/check-out based on sequence.\n"
            "First Check Time: Uses time windows to determine check-in/check-out.\n"
            "Compute with Calendar: Uses employee's work schedule.\n"
            "Device Status Code: Uses the raw status code from the device (0=check-in, 1=check-out by default).")

    # Device status code fields
    device_checkin_code = fields.Integer(string='Device Check-in Code', default=0,
        help='The status code from the device that represents a check-in (usually 0)')
    device_checkout_code = fields.Integer(string='Device Check-out Code', default=1,
        help='The status code from the device that represents a check-out (usually 1)')

    checkin_start_time = fields.Float(
        string='Check-in Start Time',
        required=True,
        default=21.0,
        help='Start of check-in period (0-23)',
    )
    checkin_end_time = fields.Float(
        string='Check-in End Time',
        required=True,
        default=1.0,
        help='End of check-in period (0-23). If less than start time, it means next day.',
    )

    grace_period = fields.Float('Grace Period (minutes)', default=15)
    ignore_holidays = fields.Boolean('Ignore Holidays', default=False)
    allow_next_day = fields.Boolean('Allow Next Day Check-out', default=False)
    next_day_limit = fields.Float('Next Day Limit (hours)', default=3.0)
    previous_day_limit = fields.Float(
        string='Previous Day Check-in Limit (Hours)',
        default=0.25,
    )

    @api.constrains('checkin_start_time', 'checkin_end_time')
    def _check_times(self):
        for record in self:
            if not (0 <= record.checkin_start_time < 24):
                raise ValidationError("Check-in start time must be between 0 and 23")
            if not (0 <= record.checkin_end_time < 24):
                raise ValidationError("Check-in end time must be between 0 and 23")
    @api.depends('end_date')
    def _compute_is_default(self):
        for record in self:
            record.is_default = not record.end_date

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.end_date and record.start_date > record.end_date:
                raise ValidationError("End date must be after start date")

            # Check for overlapping dates for same employees
            if record.employee_ids:
                overlapping = self.search([
                    ('id', '!=', record.id),
                    ('active', '=', True),
                    ('employee_ids', 'in', record.employee_ids.ids),
                    '|',
                    '&', ('start_date', '<=', record.start_date),
                    '|', ('end_date', '=', False),
                    ('end_date', '>=', record.start_date),
                    '&', ('start_date', '<=', record.end_date or record.start_date),
                    '|', ('end_date', '=', False),
                    ('end_date', '>=', record.end_date or record.start_date),
                ])
                if overlapping:
                    raise ValidationError(
                        f"Policy dates overlap with existing policies for some employees: "
                        f"{', '.join(overlapping.mapped('name'))}"
                    )

    def get_active_policy(self, employee_id, date=None):
        """Get the active policy for an employee on a specific date"""
        if not date:
            date = fields.Date.today()

        # First try to find a dated policy
        policy = self.search([
            ('employee_ids', 'in', [employee_id]),
            ('active', '=', True),
            ('start_date', '<=', date),
            '|',
            ('end_date', '=', False),
            ('end_date', '>=', date)
        ], order='end_date asc', limit=1)

        return policy