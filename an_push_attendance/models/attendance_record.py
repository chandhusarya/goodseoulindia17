from odoo import models, fields, api
from datetime import datetime, timedelta, time, date
import pytz
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError  # Add this for error handling
import logging


class AttendanceRecord(models.Model):
    _name = 'attendance.record'
    _description = 'Attendance Record'

    device_id = fields.Many2one('attendance.device', string='Device', required=True)
    pin = fields.Char(string='PIN', required=True)
    timestamp = fields.Datetime(string='Timestamp', required=True)
    timestamp_accurates = fields.Datetime(string='Timestamp accurate', compute='calc_timestamp_accurate', store=True)
    status = fields.Integer(string='Status', required=True)
    verify = fields.Integer(string='Verify', required=True)
    workcode = fields.Integer(string='Workcode')
    reserved_1 = fields.Integer(string='Reserved 1')
    reserved_2 = fields.Integer(string='Reserved 2')
    device_user_name = fields.Char(string='Device User Name', compute='_compute_device_user_name', store=True)
    mapped_employee_id = fields.Many2one('hr.employee', string='Mapped Employee', compute='_compute_mapped_employee',
                                         store=True)
    check_status = fields.Selection([
        ('check_in', 'Check In'), 
        ('check_out', 'Check Out'),
        ('repeated', 'Repeated')
    ], string='Check Status', compute='_compute_check_status', store=True)
    date_temps = fields.Date(string="Date Temp", compute="_compute_date", store=True)
    schedule_line_id = fields.Many2one('resource.calendar.attendance', compute='_compute_check_status', store=True)
    attendance_process_id = fields.Many2one('attendance.process')
    is_duplicate = fields.Boolean(string="Duplicate Entry", readonly=True, help="Indicates if this record is a potential duplicate based on grace period.")
    _sql_constraints = [
        ('unique_attendance_device_pin_timestamp',
         'UNIQUE(device_id, pin, timestamp)',
         'Duplicate attendance record detected!')
    ]

    @api.depends('timestamp_accurates')
    def _compute_date(self):
        for r in self:
            if r.timestamp_accurates:
                r.date_temps = (r.timestamp_accurates + relativedelta(hours=3)).date()
            else:
                r.date_temps = False

    @api.depends('timestamp')
    def calc_timestamp_accurate(self):
        for record in self:
            device_tz = pytz.timezone(record.device_id.device_time_zone or 'UTC')
            record_timestamp = record.timestamp.astimezone(device_tz)
            if record_timestamp.time() <= self.float_to_time(
                    23.99).max and record_timestamp.time() >= self.float_to_time(23.75):
                time_without_time_zone = record_timestamp + relativedelta(hours=1)
                timestamp = datetime.combine(time_without_time_zone, self.float_to_time(0))

                record.timestamp_accurates = timestamp - relativedelta(hours=3)
            else:
                record.timestamp_accurates = record.timestamp

    @api.depends('pin', 'device_id')
    def _compute_device_user_name(self):
        for record in self:
            user = self.env['device.user'].search([('device_id', '=', record.device_id.id), ('pin', '=', record.pin)],
                                                  limit=1)
            record.device_user_name = user.name if user else ''

    @api.depends('pin', 'device_id')
    def _compute_mapped_employee(self):
        for record in self:
            user = self.env['device.user'].search([('device_id', '=', record.device_id.id), ('pin', '=', record.pin)],
                                                  limit=1)
            record.mapped_employee_id = user.employee_id if user else None


    day_period = fields.Selection([
        ('regular', 'Regular Day'),
        ('weekend', 'Weekend'),
        ('holiday', 'Holiday')
    ], string='Day Period')


    shift_day_period = fields.Selection([
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon')
    ], string='Shift Period', store=True)


    shift_line_id = fields.Many2one('resource.calendar.attendance', string='Shift Line', store=True)

    @api.model
    def process_to_attendance_process(self):
        # Get current date in UTC
        now = fields.Datetime.now()
        today = now.date()

        # Initial search for records
        domain = [
            ('attendance_process_id', '=', False),
            ('mapped_employee_id', '!=', False),
            ('is_duplicate', '=', False),  # Skip duplicate records
            ('check_status', '!=', 'repeated')  # Skip repeated records
        ]

        records = self.search(domain, order='timestamp')

        attendance_groups = {}

        for record in records:

            device_tz = pytz.timezone(record.device_id.device_time_zone or 'UTC')
            local_dt = pytz.utc.localize(record.timestamp).astimezone(device_tz)

            # Handle after-midnight case
            if 0 <= local_dt.hour < 3:
                date = (local_dt - timedelta(days=1)).date()
            else:
                date = local_dt.date()

            key = (record.mapped_employee_id.id, date)
            
            if key not in attendance_groups:
                attendance_groups[key] = []
            attendance_groups[key].append(record)

        for (employee_id, date), group_records in attendance_groups.items():
            try:
                # Convert date object to datetime.date if needed
                if isinstance(date, datetime):
                    record_date = date.date()
                else:
                    record_date = date

                # Skip processing if it's today's date and there's only one record
                if record_date == today and len(group_records) == 1:
                    continue

                # Sort records by timestamp
                sorted_records = sorted(group_records, key=lambda r: r.timestamp)
                
                # Group records into check-in/check-out pairs
                current_pair = []
                pairs = []
                
                for record in sorted_records:
                    if not current_pair and record.check_status == 'check_in':
                        # Start new pair with check-in
                        current_pair = [record]
                    elif current_pair and record.check_status == 'check_out':
                        # Complete pair with check-out
                        current_pair.append(record)
                        pairs.append(current_pair)
                        current_pair = []
                    elif current_pair and record.check_status == 'check_in':
                        # Found new check-in without check-out, close previous pair
                        pairs.append(current_pair)
                        current_pair = [record]
                
                # Handle any remaining pair
                if current_pair:
                    pairs.append(current_pair)

                # Create attendance process for each pair
                for pair in pairs:
                    check_in_record = pair[0]
                    check_out_record = pair[1] if len(pair) > 1 else None
                    
                    process_vals = {
                        'employee_id': employee_id,
                        'device_id': check_in_record.device_id.id,
                        'check_in': check_in_record.timestamp,
                        'check_out': check_out_record.timestamp if check_out_record else False,
                        'shift_day_period': check_in_record.shift_day_period
                    }

                    process = self.env['attendance.process'].create(process_vals)

                    # Link records to process
                    for record in pair:
                        record.write({'attendance_process_id': process.id})

            except Exception as e:
                continue

    def reset_processing_status(self):
        """Reset the processing status to allow reprocessing"""
        self.ensure_one()
        if self.attendance_process_id:
            # Remove link to attendance process
            self.write({
                'attendance_process_id': False,
                'check_status': False  # Reset status to allow recomputation
            })

            # Recompute check status
            self._compute_check_status()

    def determine_check_status_for_unscheduled(self, record, local_dt):
        """Helper method to determine check status for unscheduled periods"""
        # Get all records for the same day
        day_start = local_dt.replace(hour=0, minute=0, second=0)
        day_end = day_start + timedelta(days=1)

        day_records = self.search([
            ('mapped_employee_id', '=', record.mapped_employee_id.id),
            ('timestamp', '>=', day_start),
            ('timestamp', '<', day_end)
        ], order='timestamp')

        if day_records:
            if day_records[0].id == record.id:
                return 'check_in'
            elif day_records[-1].id == record.id:
                return 'check_out'
        return False


    def recheck_statuses(self):
        """Recompute check status for selected records"""
        if not self:
            # If empty selection, recheck all records
            self = self.search([])

        # Get grace period from system parameter (default 3 minutes)
        grace_period = int(self.env['ir.config_parameter'].sudo().get_param('attendance.grace_period', '3'))

        # 1. Clear existing statuses in bulk SQL operation
        if self.ids:
            self._cr.execute("""
                UPDATE attendance_record
                SET check_status = NULL,
                    shift_day_period = NULL,
                    shift_line_id = NULL,
                    is_duplicate = FALSE
                WHERE id IN %s
            """, [tuple(self.ids) if len(self.ids) > 1 else (self.ids[0],)])

        # 2. Process in employee-date batches
        employees = self.mapped('mapped_employee_id')
        
        for emp in employees:
            if not emp:
                continue

            # Get all records for this employee
            emp_records = self.filtered(lambda r: r.mapped_employee_id == emp)

            # Group by local date (using device timezone)
            date_groups = {}
            for record in emp_records:
                device_tz = pytz.timezone(record.device_id.device_time_zone or 'UTC')
                local_dt = record.timestamp.astimezone(device_tz)
                date_key = local_dt.date()
                if date_key not in date_groups:
                    date_groups[date_key] = self.env['attendance.record']
                date_groups[date_key] |= record

            # Process each day's records
            for date, day_records in date_groups.items():
                # Sort records by timestamp to ensure proper processing
                sorted_records = day_records.sorted(lambda r: r.timestamp)
                
                # Process each record using _compute_check_status
                for record in sorted_records:
                    record._compute_check_status()

    def _try_match_calendar(self, record):
        """Check if record matches any scheduled period, with proper shift transitions"""
        employee = record.mapped_employee_id
        if not employee or not employee.resource_calendar_id:
            return False

        schedule = employee.resource_calendar_id
        device_tz = pytz.timezone(record.device_id.device_time_zone or 'UTC')
        local_dt = record.timestamp.astimezone(device_tz)
        current_time = local_dt.hour + local_dt.minute / 60.0

        # Get weekday (0-6, Monday is 0)
        weekday = str(local_dt.weekday())

        # Get schedule lines for this weekday
        schedule_lines = schedule.attendance_ids.filtered(
            lambda x: x.dayofweek == weekday
        ).sorted(key=lambda x: x.hour_from)

        if not schedule_lines:
            return False

        # Check each period
        for line in schedule_lines:
            start_time = float(line.start_period or line.hour_from)
            end_time = float(line.end_period or line.hour_to)

            # Define grace periods for check-in/out (30 minutes)
            start_grace = start_time - 0.5  # 30 minutes before start
            end_grace = end_time + 0.5  # 30 minutes after end

            # Check if time falls within period (including grace)
            if start_grace <= current_time <= end_grace:
                return line

        return False


    def _get_default_grace_period(self):
        return float(self.env['ir.config_parameter'].sudo().get_param(
            'attendance.default_grace_period', '15.0'))

    def _get_policy_settings(self, employee):
        """Get policy settings for an employee"""
        
        # Get active policy for today
        today = fields.Date.today()
        policy = self.env['fp.status.policy'].get_active_policy(employee.id, today)

        return {
            'grace_period': policy.grace_period if policy else 15.0,
            'policy_type': policy.policy_type if policy else 'flexible_period',
            'checkin_start_time': policy.checkin_start_time if policy else 21.0,
            'checkin_end_time': policy.checkin_end_time if policy else 1.0,
            'allow_next_day': policy.allow_next_day if policy else False,
            'next_day_limit': policy.next_day_limit if policy else 3.0,
            'previous_day_limit': policy.previous_day_limit if policy else 0.25,
        }

    def _compute_check_status(self):
        """Main compute method for attendance status"""
        for record in self:
            try:
                vals = {}
                employee = record.mapped_employee_id

                if not employee:
                    # Default hardcoded rule for unmapped PINs:
                    # If status is 0, it's a check-in, otherwise it's a check-out
                    if record.status == 0:
                        check_status = 'check_in'
                    else:
                        check_status = 'check_out'
                    
                    vals.update({
                        'check_status': check_status,
                        'shift_day_period': False
                    })
                    record.write(vals)
                    continue

                # Get device timezone
                device_tz = pytz.timezone(record.device_id.device_time_zone or 'UTC')
                local_dt = record.timestamp.astimezone(device_tz)
                record_date = local_dt.date()
                
                # Get the active policy for this employee on this date
                policy = self.env['fp.status.policy'].get_active_policy(employee.id, record_date)
                policy_type = policy.policy_type if policy else 'flexible_period'  # Default to flexible period if no policy
                
                # Get grace period from system parameter or policy
                grace_period = int(self.env['ir.config_parameter'].sudo().get_param('attendance.grace_period', '3'))
                if policy:
                    grace_period = policy.grace_period
                
                # Check for duplicates within grace period
                prev_record = self.search([
                    ('mapped_employee_id', '=', record.mapped_employee_id.id),
                    ('timestamp', '<', record.timestamp),
                    ('is_duplicate', '=', False)
                ], order='timestamp desc', limit=1)
                
                if prev_record:
                    time_diff_minutes = (record.timestamp - prev_record.timestamp).total_seconds() / 60
                    if time_diff_minutes <= grace_period:
                        vals.update({
                            'check_status': 'repeated',
                            'shift_day_period': prev_record.shift_day_period,
                            'shift_line_id': prev_record.shift_line_id.id if prev_record.shift_line_id else False,
                            'is_duplicate': True
                        })
                        record.write(vals)
                        continue
                
                # Special handling for compute_with_calendar policy to check for overnight shifts
                if policy_type == 'compute_with_calendar':
                    # Check if this is an early morning record that might be part of an overnight shift
                    current_time = local_dt.hour + local_dt.minute / 60.0
                    if current_time < 5.0:  # Early morning (before 5 AM)
                        prev_day = record_date - timedelta(days=1)
                        prev_day_policy = self.env['fp.status.policy'].get_active_policy(employee.id, prev_day)
                        
                        if prev_day_policy and prev_day_policy.policy_type == 'compute_with_calendar' and prev_day_policy.allow_next_day:
                            # Check for overnight shifts in the employee's schedule
                            if employee.resource_calendar_id:
                                prev_weekday = str((local_dt.weekday() - 1) % 7)  # Previous day's weekday
                                prev_day_schedule_lines = employee.resource_calendar_id.attendance_ids.filtered(
                                    lambda x: x.dayofweek == prev_weekday
                                ).sorted(key=lambda x: x.hour_from)
                                
                                overnight_shifts = prev_day_schedule_lines.filtered(
                                    lambda x: float(x.end_period or x.hour_to) < float(x.start_period or x.hour_from)
                                )

                if not policy:
                    # Default behavior if no policy
                    self._compute_with_policy(record, vals)
                elif policy_type == 'first_check_time':
                    self._compute_first_check_time(record, vals, policy)
                elif policy_type == 'device_status_code':
                    self._compute_device_status_code(record, vals, policy)
                elif policy_type == 'compute_with_calendar':
                    self._compute_with_calendar(record, vals)
                else:  # flexible_period or any other type
                    self._compute_with_policy(record, vals)

                if vals:
                    record.write(vals)

            except Exception:
                record.write({
                    'check_status': 'check_in',
                    'shift_day_period': False
                })

    def _compute_device_status_code(self, record, vals, policy):
        """Determine check status based on device status code"""
        try:
            # Get device timezone
            device_tz = pytz.timezone(record.device_id.device_time_zone or 'UTC')
            local_dt = record.timestamp.astimezone(device_tz)
            
            # Determine morning/afternoon based on time
            if local_dt.hour < 12:
                shift_period = 'morning'
            else:
                shift_period = 'afternoon'
            
            # Get previous record for default behavior
            prev_record = self.search([
                ('mapped_employee_id', '=', record.mapped_employee_id.id),
                ('timestamp', '<', record.timestamp),
                ('is_duplicate', '=', False)
            ], order='timestamp desc', limit=1)
            
            # Determine check status based on device status code - use strict equality comparison
            if record.status == policy.device_checkin_code:
                check_status = 'check_in'
            elif record.status == policy.device_checkout_code:
                check_status = 'check_out'
            else:
                # For any other status code, use default behavior
                if not prev_record:
                    check_status = 'check_in'
                else:
                    check_status = 'check_out' if prev_record.check_status == 'check_in' else 'check_in'
            
            vals.update({
                'check_status': check_status,
                'shift_day_period': shift_period,
                'is_duplicate': False
            })
            
        except Exception:
            vals.update({
                'check_status': 'check_in',
                'shift_day_period': 'morning',
                'is_duplicate': False
            })

    def _compute_first_check_time(self, record, vals, policy):
        """First check time policy processing for overnight and same-day periods"""
        try:
            device_tz = pytz.timezone(record.device_id.device_time_zone or 'UTC')
            local_dt = record.timestamp.astimezone(device_tz)
            current_time = local_dt.hour + local_dt.minute / 60.0

            # Use policy's configured check-in window
            checkin_start = policy.checkin_start_time  # e.g., 18.0 for 18:00
            checkin_end = policy.checkin_end_time  # e.g., 23.0 for 23:00

            # Determine if time is within check-in period
            is_checkin_period = False
            base_date = local_dt.date()

            # Case 1: Normal window (e.g., 18:00-23:00)
            if checkin_start <= current_time <= 23.99:
                is_checkin_period = True
            # Case 2: Overnight window (e.g., 00:00-01:00 next day)
            elif 0 <= current_time <= checkin_end and checkin_end < checkin_start:
                is_checkin_period = True
                base_date = local_dt.date() - timedelta(days=1)

            # Set check status based on period
            if is_checkin_period:
                vals.update({
                    'check_status': 'check_in',
                    'shift_day_period': 'morning',
                    'is_duplicate': False
                })
            else:
                # For records outside check-in window, look for a previous check-in
                # First, check for a check-in on the same day
                same_day_checkin = self.search([
                    ('mapped_employee_id', '=', record.mapped_employee_id.id),
                    ('timestamp', '>=', datetime.combine(local_dt.date(), time(0, 0)).astimezone(pytz.UTC)),
                    ('timestamp', '<', record.timestamp),
                    ('check_status', '=', 'check_in'),
                    ('is_duplicate', '=', False)
                ], order='timestamp desc', limit=1)
                
                if same_day_checkin:
                    vals.update({
                        'check_status': 'check_out',
                        'shift_day_period': same_day_checkin.shift_day_period,
                        'is_duplicate': False
                    })
                    return
                
                # If no same-day check-in, look for a check-in from the previous day
                # that doesn't have a matching check-out
                prev_day = local_dt.date() - timedelta(days=1)
                prev_day_start = datetime.combine(prev_day, time(0, 0)).astimezone(pytz.UTC)
                prev_day_end = datetime.combine(prev_day, time(23, 59, 59)).astimezone(pytz.UTC)
                
                prev_day_checkins = self.search([
                    ('mapped_employee_id', '=', record.mapped_employee_id.id),
                    ('timestamp', '>=', prev_day_start),
                    ('timestamp', '<=', prev_day_end),
                    ('check_status', '=', 'check_in'),
                    ('is_duplicate', '=', False)
                ], order='timestamp desc')
                
                # Get all check-outs for the previous day
                prev_day_checkouts = self.search([
                    ('mapped_employee_id', '=', record.mapped_employee_id.id),
                    ('timestamp', '>=', prev_day_start),
                    ('timestamp', '<=', prev_day_end),
                    ('check_status', '=', 'check_out'),
                    ('is_duplicate', '=', False)
                ])
                
                # Find check-ins without matching check-outs
                unmatched_checkin = False
                for checkin in prev_day_checkins:
                    has_checkout = False
                    for checkout in prev_day_checkouts:
                        if checkout.timestamp > checkin.timestamp:
                            has_checkout = True
                            break
                    if not has_checkout:
                        unmatched_checkin = checkin
                        break
                
                if unmatched_checkin:
                    vals.update({
                        'check_status': 'check_out',
                        'shift_day_period': unmatched_checkin.shift_day_period,
                        'is_duplicate': False
                    })
                else:
                    # If no unmatched check-in found, default to check-in
                    vals.update({
                        'check_status': 'check_in',
                        'shift_day_period': 'morning',
                        'is_duplicate': False
                    })

        except Exception:
            vals.update({
                'check_status': 'check_in',
                'shift_day_period': 'morning',
                'is_duplicate': False
            })



    def _compute_flexible_period(self, record, vals, settings):
        """Flexible period policy implementation"""
        try:
            device_tz = pytz.timezone(record.device_id.device_time_zone or 'UTC')
            local_dt = record.timestamp.astimezone(device_tz)

            # Get all records for the same day
            day_start = local_dt.replace(hour=0, minute=0, second=0)
            day_end = day_start + timedelta(days=1)

            day_records = self.search([
                ('mapped_employee_id', '=', record.mapped_employee_id.id),
                ('timestamp', '>=', day_start),
                ('timestamp', '<', day_end),
                ('is_duplicate', '=', False)
            ], order='timestamp')

            if not day_records or day_records[0].id == record.id:
                # First record of the day
                vals.update({
                    'check_status': 'check_in',
                    'shift_day_period': 'morning',
                    'is_duplicate': False
                })
                return

            # Get the previous non-duplicate record
            record_index = list(day_records).index(record)
            prev_record = day_records[record_index - 1]

            # Calculate time difference from previous record
            time_diff = (record.timestamp - prev_record.timestamp).total_seconds() / 60

            # Get minimum interval between check-in/check-out (default 1 minute if not set)
            min_interval = settings.get('min_interval_minutes', 1)

            # Outside grace period - alternate check status if enough time has passed
            if time_diff >= min_interval:
                vals.update({
                    'is_duplicate': False,
                    'check_status': 'check_out' if prev_record.check_status == 'check_in' else 'check_in',
                    'shift_day_period': prev_record.shift_day_period
                })
            else:
                # Not enough time passed - use same status
                vals.update({
                    'is_duplicate': False,
                    'check_status': prev_record.check_status,
                    'shift_day_period': prev_record.shift_day_period
                })

        except Exception:
            vals.update({
                'check_status': 'check_in',
                'shift_day_period': 'morning',
                'is_duplicate': False
            })


    def test_specific_record_sql(self):
        """Method that can be called from SQL"""
        # Use SQL to get records
        self.env.cr.execute("""
            SELECT ar.id 
            FROM attendance_record ar
            JOIN hr_employee he ON ar.mapped_employee_id = he.id
            WHERE he.name = 'ASIM MUHAMMAD MUSTAFA'
            AND ar.timestamp >= '2025-01-01 00:00:00'
            AND ar.timestamp < '2025-01-02 00:00:00'
            ORDER BY ar.timestamp
        """)
        record_ids = [r[0] for r in self.env.cr.fetchall()]

        # Process each record
        for record_id in record_ids:
            record = self.browse(record_id)
            vals = {}

            # Get employee policy settings
            employee = record.mapped_employee_id
            settings = self._get_policy_settings(employee)

            # Process with first check time
            self._compute_first_check_time(record, vals, settings)

            # Update record using SQL to avoid triggers
            if vals:
                self.env.cr.execute("""
                    UPDATE attendance_record 
                    SET check_status = %s,
                        shift_day_period = %s,
                        is_duplicate = %s
                    WHERE id = %s
                """, (
                    vals.get('check_status'),
                    vals.get('shift_day_period'),
                    vals.get('is_duplicate', False),
                    record.id
                ))

        self.env.cr.commit()

    def _compute_with_calendar(self, record, vals):
        """Compute based on calendar schedule"""
        employee = record.mapped_employee_id
        if not employee or not employee.resource_calendar_id:
            return False

        schedule = employee.resource_calendar_id
        device_tz = pytz.timezone(record.device_id.device_time_zone or 'UTC')
        local_dt = record.timestamp.astimezone(device_tz)
        current_time = local_dt.hour + local_dt.minute / 60.0

        # Get weekday (0-6, Monday is 0)
        weekday = str(local_dt.weekday())

        # First, check if this is an early morning record that belongs to previous day's overnight shift
        if current_time < 5.0:  # Early morning (before 5 AM)
            prev_day = local_dt.date() - timedelta(days=1)
            prev_weekday = str((int(weekday) - 1) % 7)  # Previous day's weekday
            
            # Get previous day's schedule lines
            prev_schedule_lines = schedule.attendance_ids.filtered(
                lambda x: x.dayofweek == prev_weekday
            ).sorted(key=lambda x: x.hour_from)
            
            # Find overnight shifts from previous day
            overnight_shifts = prev_schedule_lines.filtered(
                lambda x: float(x.end_period or x.hour_to) < float(x.start_period or x.hour_from)
            )
            
            if overnight_shifts:
                for shift in overnight_shifts:
                    start_time = float(shift.start_period or shift.hour_from)
                    end_time = float(shift.end_period or shift.hour_to)
                    
                    # For overnight comparison
                    if current_time <= end_time:
                        # Find the period records from previous day's shift
                        prev_day_start = datetime.combine(prev_day, 
                            self.float_to_time(start_time)).replace(tzinfo=device_tz)
                        next_day_end = datetime.combine(local_dt.date(), 
                            self.float_to_time(end_time)).replace(tzinfo=device_tz)
                        
                        # Convert to UTC for database search
                        prev_day_start_utc = prev_day_start.astimezone(pytz.UTC)
                        next_day_end_utc = next_day_end.astimezone(pytz.UTC)
                        
                        # Find all records in this overnight period
                        overnight_records = self.search([
                            '|',
                            ('id', '=', record.id),
                            '&', '&', '&',
                            ('mapped_employee_id', '=', record.mapped_employee_id.id),
                            ('timestamp', '>=', prev_day_start_utc),
                            ('timestamp', '<=', next_day_end_utc),
                            ('is_duplicate', '=', False)
                        ], order='timestamp')
                        
                        if overnight_records:
                            # If this is the last record in the overnight period, mark as check-out
                            if overnight_records[-1].id == record.id:
                                vals.update({
                                    'check_status': 'check_out',
                                    'shift_day_period': shift.day_period,
                                    'shift_line_id': shift.id
                                })
                                return True
                            # If there are other records after this one in the overnight period
                            elif len(overnight_records) > 1 and overnight_records[0].id != record.id:
                                # Find position in sequence
                                record_ids = overnight_records.ids
                                record_index = record_ids.index(record.id)
                                
                                if record_index > 0:
                                    prev_record = overnight_records.browse(record_ids[record_index-1])
                                    if prev_record.check_status == 'check_in':
                                        vals.update({
                                            'check_status': 'check_out',
                                            'shift_day_period': shift.day_period,
                                            'shift_line_id': shift.id
                                        })
                                        return True

        # Get schedule lines for this weekday
        schedule_lines = schedule.attendance_ids.filtered(
            lambda x: x.dayofweek == weekday
        ).sorted(key=lambda x: x.hour_from)
        
        if not schedule_lines:
            return False

        # Check each period
        for line in schedule_lines:
            start_time = float(line.start_period or line.hour_from)
            end_time = float(line.end_period or line.hour_to)

            # Handle overnight shifts
            is_overnight = end_time < start_time
            adjusted_current_time = current_time
            
            if is_overnight:
                # For overnight shifts, end_time is in the next day
                adjusted_end_time = end_time + 24
                
                # Only adjust current_time if it's early morning (before end_time)
                # or if it's after start_time in the evening
                if current_time < end_time:
                    # Early morning of the next day
                    adjusted_current_time = current_time + 24
                elif current_time >= start_time:
                    # Evening of the current day - no adjustment needed
                    pass
                else:
                    # Daytime hours outside the shift - no need to adjust
                    pass
            else:
                adjusted_end_time = end_time

            # Check if time falls within period
            if start_time <= adjusted_current_time <= adjusted_end_time:
                # Find all records for this employee within this period
                # Convert to UTC for database search
                local_date = local_dt.date()
                period_start_local = datetime.combine(local_date, 
                    self.float_to_time(start_time)).replace(tzinfo=device_tz)
                period_end_local = datetime.combine(local_date, 
                    self.float_to_time(end_time % 24)).replace(tzinfo=device_tz)
                
                if is_overnight:
                    period_end_local += timedelta(days=1)
                
                # Convert to UTC for database search
                period_start_utc = period_start_local.astimezone(pytz.UTC)
                period_end_utc = period_end_local.astimezone(pytz.UTC)

                # Include the current record explicitly
                period_records = self.search([
                    '|',
                    ('id', '=', record.id),
                    '&', '&', '&',
                    ('mapped_employee_id', '=', record.mapped_employee_id.id),
                    ('timestamp', '>=', period_start_utc),
                    ('timestamp', '<=', period_end_utc),
                    ('is_duplicate', '=', False)
                ], order='timestamp')

                # Determine if this is first or last record in period
                if period_records:
                    if len(period_records) == 1 and record.id == period_records[0].id:
                        # If only one record in period, mark as check-in
                        vals.update({
                            'check_status': 'check_in',
                            'shift_day_period': line.day_period,
                            'shift_line_id': line.id
                        })
                    elif period_records[0].id == record.id:
                        vals.update({
                            'check_status': 'check_in',
                            'shift_day_period': line.day_period,
                            'shift_line_id': line.id
                        })
                    elif period_records[-1].id == record.id:
                        vals.update({
                            'check_status': 'check_out',
                            'shift_day_period': line.day_period,
                            'shift_line_id': line.id
                        })
                    else:
                        # Middle records - find position in sequence
                        record_ids = period_records.ids
                        record_index = record_ids.index(record.id)
                        
                        if record_index > 0:
                            prev_record = period_records.browse(record_ids[record_index-1])
                            if prev_record.check_status == 'check_in':
                                vals.update({
                                    'check_status': 'check_out',
                                    'shift_day_period': line.day_period,
                                    'shift_line_id': line.id
                                })
                            else:
                                vals.update({
                                    'check_status': 'check_in',
                                    'shift_day_period': line.day_period,
                                    'shift_line_id': line.id
                                })
                        else:
                            vals.update({
                                'check_status': 'check_in',
                                'shift_day_period': line.day_period,
                                'shift_line_id': line.id
                            })
                else:
                    # This should never happen since we're explicitly including the current record
                    vals.update({
                        'check_status': 'check_in',
                        'shift_day_period': line.day_period,
                        'shift_line_id': line.id
                    })
                return True

        # For records that don't fall within any schedule period, use a default behavior
        # based on the time of day and previous records
        try:
            # Get all records for the same day
            day_start = local_dt.replace(hour=0, minute=0, second=0)
            day_end = day_start + timedelta(days=1)
            
            day_records = self.search([
                ('mapped_employee_id', '=', record.mapped_employee_id.id),
                ('timestamp', '>=', day_start.astimezone(pytz.UTC)),
                ('timestamp', '<', day_end.astimezone(pytz.UTC)),
                ('is_duplicate', '=', False)
            ], order='timestamp')
            
            # Determine check status based on previous records
            if not day_records or day_records[0].id == record.id:
                # First record of the day
                vals.update({
                    'check_status': 'check_in',
                    'shift_day_period': 'morning' if current_time < 12 else 'afternoon',
                    'is_duplicate': False
                })
                return True
            else:
                # Find the previous record's status
                record_ids = day_records.ids
                if record.id in record_ids:
                    record_index = record_ids.index(record.id)
                    if record_index > 0:
                        prev_record = day_records.browse(record_ids[record_index-1])
                        if prev_record.check_status == 'check_in':
                            vals.update({
                                'check_status': 'check_out',
                                'shift_day_period': 'morning' if current_time < 12 else 'afternoon',
                                'is_duplicate': False
                            })
                        else:
                            vals.update({
                                'check_status': 'check_in',
                                'shift_day_period': 'morning' if current_time < 12 else 'afternoon',
                                'is_duplicate': False
                            })
                        return True
        except Exception:
            pass
        
        # If all else fails, default to check-in
        vals.update({
            'check_status': 'check_in',
            'shift_day_period': 'morning' if current_time < 12 else 'afternoon',
            'is_duplicate': False
        })
        return True

    def _compute_with_policy(self, record, vals):
        """Handle attendance records with flexible policy time limits"""
        try:
            device_tz = pytz.timezone(record.device_id.device_time_zone or 'UTC')
            local_dt = record.timestamp.astimezone(device_tz)
            current_time = local_dt.hour + local_dt.minute / 60.0

            # Get policy settings
            employee = record.mapped_employee_id
            policy = employee.fp_policy_ids[0] if employee.fp_policy_ids else None
            grace_period = policy.grace_period if policy else 15.0

            # Get all records for the same day
            day_start = local_dt.replace(hour=0, minute=0, second=0)
            day_end = day_start + timedelta(days=1)

            day_records = self.search([
                ('mapped_employee_id', '=', record.mapped_employee_id.id),
                ('timestamp', '>=', day_start.astimezone(pytz.UTC)),
                ('timestamp', '<', day_end.astimezone(pytz.UTC)),
                ('is_duplicate', '=', False)
            ], order='timestamp')

            # If first record of the day or no previous records
            if not day_records or day_records[0].id == record.id:
                vals.update({
                    'is_duplicate': False,
                    'check_status': 'check_in',
                    'shift_day_period': 'morning'
                })
            else:
                # Find the previous non-duplicate record
                prev_status = None
                for rec in day_records:
                    if rec.id == record.id:
                        break
                    if not rec.is_duplicate:
                        prev_status = rec.check_status

                # Alternate check-in/out based on previous status
                if prev_status == 'check_in':
                    vals.update({
                        'is_duplicate': False,
                        'check_status': 'check_out',
                        'shift_day_period': 'morning' if current_time < 12 else 'afternoon'
                    })
                else:
                    vals.update({
                        'is_duplicate': False,
                        'check_status': 'check_in',
                        'shift_day_period': 'morning' if current_time < 12 else 'afternoon'
                    })

        except Exception as e:
            vals.update({
                'check_status': 'check_in',
                'shift_day_period': 'morning',
                'is_duplicate': False
            })

    def _determine_check_status(self, record, schedule_line):
        """Helper method to determine check status within a schedule period"""
        device_tz = pytz.timezone(record.device_id.device_time_zone or 'UTC')
        local_dt = record.timestamp.astimezone(device_tz)
        current_time = local_dt.hour + local_dt.minute / 60.0

        start_time = float(schedule_line.start_period or schedule_line.hour_from)
        end_time = float(schedule_line.end_period or schedule_line.hour_to)

        # First hour of shift is check-in period
        if current_time <= (start_time + 1):
            return 'check_in'
        # Last hour of shift is check-out period
        elif current_time >= (end_time - 1):
            return 'check_out'
        # For times in between, use previous records to determine
        else:
            period_start = datetime.combine(local_dt.date(),
                                            self.float_to_time(start_time))
            period_end = datetime.combine(local_dt.date(),
                                          self.float_to_time(end_time))

            if period_end < period_start:
                period_end += timedelta(days=1)

            period_records = self.search([
                ('mapped_employee_id', '=', record.mapped_employee_id.id),
                ('timestamp', '>=', period_start.astimezone(pytz.UTC)),
                ('timestamp', '<=', period_end.astimezone(pytz.UTC))
            ], order='timestamp')

            if period_records[0].id == record.id:
                return 'check_in'
            else:
                return 'check_out'

    def float_to_time(self, float_time):
        """Convert float time to time object, handling overnight shifts"""
        if not float_time:
            return time(0, 0)

        hours = int(float_time)
        minutes = int((float_time % 1) * 60)

        # Handle overnight shifts
        if hours >= 24:
            hours = hours % 24

        return time(hours, minutes)






    @api.model
    def process_data(self):
        """Process attendance records into hr.attendance entries"""
        
        records = self.search([
            ('attendance_process_id', '=', False),
            ('mapped_employee_id', '!=', False),
            ('is_duplicate', '=', False)
        ], order='timestamp')

        attendance_groups = {}
        
        for record in records:
            if not record.shift_line_id:
                continue
            
            key = (record.mapped_employee_id.id, record.shift_line_id.id)
            if key not in attendance_groups:
                attendance_groups[key] = []
            attendance_groups[key].append(record)

        for (employee_id, shift_line_id), group_records in attendance_groups.items():
            if len(group_records) < 1:
                continue
            
            # Sort records by timestamp
            sorted_records = sorted(group_records, key=lambda r: r.timestamp)
            
            # First record is check-in, last record is check-out
            check_in_record = sorted_records[0]
            check_out_record = sorted_records[-1] if len(sorted_records) > 1 else None
            
            if check_in_record:
                # Create hr.attendance
                self.env['hr.attendance'].create({
                    'employee_id': employee_id,
                    'check_in': check_in_record.timestamp,
                    'check_out': check_out_record.timestamp if check_out_record else check_in_record.timestamp,
                    'shift_line_id': shift_line_id
                })
                
                # Mark records as processed
                for record in group_records:
                    record.write({'attendance_process_id': self.env['attendance.process'].create({}).id})


    def _is_valid_check_out(self, check_in, check_out):
        """Check if check-out belongs to this check-in based on shift and timing"""
        device_tz = pytz.timezone(check_in.device_id.device_time_zone or 'UTC')

        check_in_local = pytz.utc.localize(check_in.timestamp).astimezone(device_tz)
        check_out_local = pytz.utc.localize(check_out.timestamp).astimezone(device_tz)

        # If check-out is before check-in in local time, add a day to check-out
        if check_out_local < check_in_local:
            check_out_local = check_out_local + timedelta(days=1)

        # Calculate time difference in hours
        time_diff = (check_out_local - check_in_local).total_seconds() / 3600

        # Valid range: between 2 and 12 hours for a shift
        return 2 <= time_diff <= 12

    def _find_matching_check_out(self, check_in, processed_records):
        """Find the best matching check-out for this check-in"""
        device_tz = pytz.timezone(check_in.device_id.device_time_zone or 'UTC')
        check_in_local = pytz.utc.localize(check_in.timestamp).astimezone(device_tz)

        matching_check_outs = [
            r for r in processed_records
            if r.check_status == 'check_out'
               and r.shift_day_period == check_in.shift_day_period
               and not r.attendance_process_id
               and self._is_valid_check_out(check_in, r)
        ]

        if matching_check_outs:
            # Return the closest check-out by time difference
            return min(matching_check_outs, key=lambda x: abs(
                (pytz.utc.localize(x.timestamp).astimezone(device_tz) - check_in_local).total_seconds()
            ))

        return None

    def _create_attendance_process(self, employee_id, check_in_record, check_out_record, shift_period):
        """Create attendance process and related records"""
        process = self.env['attendance.process'].create({
            'employee_id': employee_id,
            'device_id': check_in_record.device_id.id,
            'check_in': check_in_record.timestamp,
            'check_out': check_out_record.timestamp,
            'shift_day_period': shift_period
        })

        # Link records to process
        check_in_record.attendance_process_id = process.id
        check_out_record.attendance_process_id = process.id

        # Create attendance record
        self.env['hr.attendance'].with_context(no_check_overlap=True).create({
            'employee_id': employee_id,
            'check_in': check_in_record.timestamp,
            'check_out': check_out_record.timestamp,
            'process_id': process.id
        })


    def _process_shift_sequence(self, employee_id, shift_records, shift_period):
        try:
            # Get first record's device
            device_id = shift_records[0].device_id.id

            # Handle sequences
            sequences = []
            current_sequence = []

            for record in shift_records:
                if not current_sequence:
                    current_sequence.append(record)
                    continue

                time_diff = (record.timestamp - current_sequence[-1].timestamp).total_seconds() / 3600

                # If time difference is more than 1 hour, start new sequence
                if time_diff > 1:
                    sequences.append(current_sequence)
                    current_sequence = [record]
                else:
                    current_sequence.append(record)

            if current_sequence:
                sequences.append(current_sequence)

            # Process each sequence
            for sequence in sequences:
                try:
                    if len(sequence) == 1:
                        # Single record - duplicate it
                        record = sequence[0]
                        process = self.env['attendance.process'].create({
                            'employee_id': employee_id,
                            'device_id': device_id,
                            'check_in': record.timestamp,
                            'check_out': record.timestamp,
                            'shift_day_period': shift_period
                        })

                        record.attendance_process_id = process.id

                        # Create HR attendance with force skipping validation
                        self.env['hr.attendance'].with_context(no_check_overlap=True).create({
                            'employee_id': employee_id,
                            'check_in': record.timestamp,
                            'check_out': record.timestamp,
                            'process_id': process.id
                        })
                    else:
                        # Multiple records - use first as check-in, last as check-out
                        process = self.env['attendance.process'].create({
                            'employee_id': employee_id,
                            'device_id': device_id,
                            'check_in': sequence[0].timestamp,
                            'check_out': sequence[-1].timestamp,
                            'shift_day_period': shift_period
                        })

                        for record in sequence:
                            record.attendance_process_id = process.id

                        # Create HR attendance with force skipping validation
                        self.env['hr.attendance'].with_context(no_check_overlap=True).create({
                            'employee_id': employee_id,
                            'check_in': sequence[0].timestamp,
                            'check_out': sequence[-1].timestamp,
                            'process_id': process.id
                        })

                except Exception:
                    continue

        except Exception:
            pass






    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record._compute_device_user_name()
            record._compute_mapped_employee()
            record._compute_check_status()
        return records

    def map_device_users_to_employees(self):
        # IrConfigParam = self.env['ir.config_parameter']
        link = self.env['attendance.config.settings'].search([], limit=1)
        employee_link_field = link.employee_link_field if link else 'barcode'

        for user in self:
            if not user.mapped_employee_id:
                search_domain = [(employee_link_field, '=', user.pin)]
                employee = self.env['hr.employee'].search(search_domain, limit=1)
                if employee:
                    user.mapped_employee_id = employee



    def unlink(self):
        """Override unlink to handle batch deletions"""
        batch_size = 1000
        records = self
        while records:
            batch = records[:batch_size]
            # Detach from related records first
            batch.write({'attendance_process_id': False})
            super(AttendanceRecord, batch).unlink()
            self.env.cr.commit()  # Commit each batch
            records = records[batch_size:]
        return True

    def recheck_period(self, employee_id, start_date, end_date, do_recheck=True, do_process=True, do_hr_attendance=True):
        """Recheck attendance records for specific period and employee"""
        try:
            # Find all records for this employee in the date range
            domain = [
                ('mapped_employee_id', '=', employee_id),
            ]
            
            # Convert dates to datetime for proper comparison
            start_datetime = fields.Datetime.from_string(start_date)
            end_datetime = fields.Datetime.from_string(end_date) + relativedelta(days=1, seconds=-1)
            
            domain.extend([
                ('timestamp', '>=', start_datetime),
                ('timestamp', '<=', end_datetime)
            ])
            
            records = self.search(domain, order='timestamp')
            
            if not records:
                return 0

            if do_recheck:
                # Reset existing processes
                processes = self.env['attendance.process'].search([
                    ('employee_id', '=', employee_id),
                    ('check_in', '>=', start_datetime),
                    ('check_in', '<=', end_datetime)
                ])
                # Get related HR attendances before deleting processes
                hr_attendances = self.env['hr.attendance'].search([
                    ('process_id', 'in', processes.ids)
                ])
                # Delete HR attendances first
                hr_attendances.unlink()
                # Then delete processes
                processes.unlink()

                # Use recheck_statuses method instead of custom implementation
                records.recheck_statuses()
            
            if do_process:
                # Process only non-duplicate records to attendance process
                valid_records = records.filtered(lambda r: not r.is_duplicate)
                valid_records.process_to_attendance_process()
            
            if do_hr_attendance:
                # Get only the processes created in the selected period
                period_processes = self.env['attendance.process'].search([
                    ('employee_id', '=', employee_id),
                    ('check_in', '>=', start_datetime),
                    ('check_in', '<=', end_datetime)
                ])
                
                # Process only these specific processes to HR attendance
                if period_processes:
                    for process in period_processes:
                        if process.check_in and process.check_out:  # Only process complete records
                            self.env['hr.attendance'].with_context(no_check_overlap=True).create({
                                'employee_id': process.employee_id.id,
                                'check_in': process.check_in,
                                'check_out': process.check_out,
                                'process_id': process.id
                            })
            
            return len(records)
            
        except Exception as e:
            raise ValidationError(f"Error processing records: {str(e)}")

    @api.model
    def auto_cleanup_records(self):
        """
        Clean up old attendance records to prevent database bloat.
        Uses direct SQL for efficiency with large datasets.
        """
        try:
            # Keep records from the last 180 days (6 months)
            cutoff_date = fields.Date.today() - timedelta(days=180)
            
            # Get count of old records for logging
            self.env.cr.execute("""
                SELECT COUNT(id) FROM attendance_record
                WHERE create_date < %s
                AND attendance_process_id IS NOT NULL
            """, (cutoff_date,))
            old_count = self.env.cr.fetchone()[0]
            
            # If we have old records, delete them in batches
            if old_count > 0:
                _logger = logging.getLogger(__name__)
                _logger.info(f"Auto cleanup: Deleting {old_count} old attendance records")
                
                # Delete in batches to avoid locking issues
                self.env.cr.execute("""
                    DELETE FROM attendance_record
                    WHERE id IN (
                        SELECT id FROM attendance_record
                        WHERE create_date < %s
                        AND attendance_process_id IS NOT NULL
                        ORDER BY create_date
                        LIMIT 10000
                    )
                """, (cutoff_date,))
                
                return True
            return False
        except Exception as e:
            _logger = logging.getLogger(__name__)
            _logger.error(f"Error in auto_cleanup_records: {str(e)}")
            return False