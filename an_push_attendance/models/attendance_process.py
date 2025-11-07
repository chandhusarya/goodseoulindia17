from odoo import models, fields, api
from odoo.exceptions import ValidationError
import pytz

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    process_id = fields.Many2one('attendance.process', ondelete='set null')

    # Override the default constraint check
    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        """ This is the method we need to override to allow our custom check-in/out logic """
        for attendance in self:
            if not attendance.check_out:
                # if our attendance is coming from a process, skip validation
                if attendance.process_id:
                    continue
                # domain = [
                #     ('employee_id', '=', attendance.employee_id.id),
                #     ('check_out', '=', False),
                #     ('id', '!=', attendance.id),
                # ]
                # no_check_out = attendance.search(domain)
                # if no_check_out:
                #     raise ValidationError('Cannot create new attendance record')
            elif attendance.check_in > attendance.check_out:
                raise ValidationError('Check out must be greater than check in')

    # Remove the original compute and depends
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('process_id'):
                # Skip validation for process-created records
                continue
        return super().create(vals_list)

class AttendanceProcess(models.Model):
    _name = 'attendance.process'
    _description = 'Attendance Process'

    device_id = fields.Many2one('attendance.device', string='Device', ondelete='restrict')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, ondelete='restrict')
    check_in = fields.Datetime(string='Check In')
    check_out = fields.Datetime(string='Check Out')
    attendance_record_ids = fields.One2many('attendance.record', 'attendance_process_id', ondelete='cascade')
    shift_day_period = fields.Selection([
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon')
    ], string='Shift Period')
    date = fields.Date(string="Date", compute="_compute_date", store=True)
    attendance_id = fields.Many2one('hr.attendance', ondelete='set null')

    def unlink(self):
        """Override unlink to handle deletions properly"""
        # First detach any hr.attendance records to prevent constraint errors
        self.mapped('attendance_id').write({'process_id': False})

        # Then detach attendance records
        self.mapped('attendance_record_ids').write({'attendance_process_id': False})

        return super(AttendanceProcess, self).unlink()

    @api.depends('check_in')
    def _compute_date(self):
        for r in self:
            if r.check_in:
                r.date = r.check_in.date()
            else:
                r.date = False

    def diagnose_processing_issues(self):
        """Diagnostic method to check why records aren't being processed to HR attendance"""
        # Check eligible records
        eligible = self.search([
            ('attendance_id', '=', False),
            ('shift_day_period', '!=', False),
            ('check_in', '!=', False),
            ('check_out', '!=', False),
        ])
        
        # Return eligible records for further inspection
        return eligible

    def fix_processing_issues(self):
        """Fix common issues preventing records from being processed to HR attendance"""
        fixed_count = 0
        
        # Find records with missing shift_day_period but have at least check_in or check_out
        records_no_shift = self.search([
            ('attendance_id', '=', False),
            ('shift_day_period', '=', False),
            '|',
            ('check_in', '!=', False),
            ('check_out', '!=', False),
        ])
        
        if records_no_shift:
            for record in records_no_shift:
                # Determine shift period based on check_in time or check_out time
                reference_time = record.check_in or record.check_out
                if reference_time:
                    # Convert to user's timezone
                    user_tz = self.env.user.tz or 'UTC'
                    local_tz = pytz.timezone(user_tz)
                    local_dt = pytz.utc.localize(reference_time).astimezone(local_tz)
                    
                    # Assign morning/afternoon based on time
                    if local_dt.hour < 12:
                        record.shift_day_period = 'morning'
                    else:
                        record.shift_day_period = 'afternoon'
                    fixed_count += 1
        
        # Return number of records fixed
        return fixed_count

    def force_process_records(self, record_ids=None):
        """Force process specific attendance process records to HR attendance"""
        domain = [
            ('attendance_id', '=', False),
            # At least one of check_in or check_out must be present
            '|',
            ('check_in', '!=', False),
            ('check_out', '!=', False),
        ]
        
        # If specific record IDs are provided, add them to the domain
        if record_ids:
            domain.append(('id', 'in', record_ids))
            
        records_to_process = self.search(domain)
        
        processed_count = 0
        for record in records_to_process:
            try:
                # Ensure record has shift_day_period
                if not record.shift_day_period:
                    # Determine shift period based on check_in time or check_out time
                    user_tz = self.env.user.tz or 'UTC'
                    local_tz = pytz.timezone(user_tz)
                    
                    # Use check_in if available, otherwise use check_out
                    reference_time = record.check_in or record.check_out
                    local_dt = pytz.utc.localize(reference_time).astimezone(local_tz)
                    
                    # Assign morning/afternoon based on time
                    if local_dt.hour < 12:
                        record.shift_day_period = 'morning'
                    else:
                        record.shift_day_period = 'afternoon'
                
                # Handle incomplete records by duplicating timestamps
                check_in_time = record.check_in
                check_out_time = record.check_out
                
                # If only check-in exists, use it for check-out too
                if check_in_time and not check_out_time:
                    check_out_time = check_in_time
                
                # If only check-out exists, use it for check-in too
                elif check_out_time and not check_in_time:
                    check_in_time = check_out_time
                
                # Skip if neither check-in nor check-out exists (shouldn't happen with our domain)
                if not check_in_time or not check_out_time:
                    continue
                
                # Create HR attendance record
                attendance = self.env['hr.attendance'].with_context(no_check_overlap=True).create({
                    'employee_id': record.employee_id.id,
                    'check_in': check_in_time,
                    'check_out': check_out_time,
                    'process_id': record.id
                })
                
                # Link attendance to process
                record.attendance_id = attendance.id
                processed_count += 1
                
            except Exception:
                pass
        
        return processed_count

    def process_to_hr_attendance(self):
        # Get unprocessed records batch by batch
        batch_size = 1000
        domain = [
            ('attendance_id', '=', False),
            ('shift_day_period', '!=', False),
            # Modified: At least one of check_in or check_out must be present
            '|',
            ('check_in', '!=', False),
            ('check_out', '!=', False),
        ]
        
        # Count total eligible records
        total_records = self.search_count(domain)

        while True:
            processes = self.search(domain, limit=batch_size)
            if not processes:
                break

            for process in processes:
                try:
                    # Handle incomplete records by duplicating timestamps
                    check_in_time = process.check_in
                    check_out_time = process.check_out
                    
                    # If only check-in exists, use it for check-out too
                    if check_in_time and not check_out_time:
                        check_out_time = check_in_time
                    
                    # If only check-out exists, use it for check-in too
                    elif check_out_time and not check_in_time:
                        check_in_time = check_out_time
                    
                    # Skip if neither check-in nor check-out exists (shouldn't happen with our domain)
                    if not check_in_time or not check_out_time:
                        continue

                    # Check for existing HR attendance records for this employee and time period
                    existing_attendance = self.env['hr.attendance'].search([
                        ('employee_id', '=', process.employee_id.id),
                        ('check_in', '=', check_in_time),
                        ('check_out', '=', check_out_time),
                    ], limit=1)

                    if existing_attendance:
                        # If found, link it to the process and continue
                        process.attendance_id = existing_attendance.id
                        continue

                    # Check for overlapping attendance records
                    overlapping = self.env['hr.attendance'].search([
                        ('employee_id', '=', process.employee_id.id),
                        '|',
                        '&', ('check_in', '<=', check_in_time), ('check_out', '>=', check_in_time),
                        '&', ('check_in', '<=', check_out_time), ('check_out', '>=', check_out_time),
                    ])

                    if overlapping:
                        continue

                    # Create HR attendance record with no_check_overlap context
                    attendance = self.env['hr.attendance'].with_context(no_check_overlap=True).create({
                        'employee_id': process.employee_id.id,
                        'check_in': check_in_time,
                        'check_out': check_out_time,
                        'process_id': process.id
                    })
                    process.attendance_id = attendance.id

                except Exception:
                    continue

            self.env.cr.commit()  # Commit after each batch

    def _is_within_checkin_period(self, current_time, policy):
        """Check if time is within check-in period, handling overnight periods"""
        start_time = policy.checkin_start_time
        end_time = policy.checkin_end_time

        if end_time < start_time:
            # Overnight period case (e.g., 21:00 to 01:00)
            return (current_time >= start_time) or (current_time <= end_time)
        else:
            # Same day period case
            return start_time <= current_time <= end_time

    @api.depends('attendance_record_ids.timestamp_accurates')
    def calc_check(self):
        for r in self:
            if r.attendance_record_ids:
                r.check_in = min(set(r.attendance_record_ids.mapped('timestamp_accurates')))
                r.check_out = max(set(r.attendance_record_ids.mapped('timestamp_accurates')))
            else:
                r.check_in = False
                r.check_out = False

    @api.model
    def create_attendance_process_records(self):
        records = self.env['attendance.record'].search([
            ('check_status', 'in', ['check_in', 'check_out'])  # Filter only check_in and check_out records
        ])
        processed_dates = set()
        for record in records:
            device_tz = pytz.timezone(record.device_id.device_time_zone or 'UTC')
            local_timestamp = record.timestamp.astimezone(device_tz)
            naive_local_timestamp = local_timestamp.replace(tzinfo=None)
            date_str = naive_local_timestamp.strftime('%Y-%m-%d')
            key = (record.device_id.id, record.mapped_employee_id.id, date_str)
            if key not in processed_dates:
                processed_dates.add(key)
                check_in = record.timestamp if record.check_status == 'check_in' else None
                check_out = record.timestamp if record.check_status == 'check_out' else None
                self.create({
                    'device_id': record.device_id.id,
                    'employee_id': record.mapped_employee_id.id,
                    'check_in': check_in,
                    'check_out': check_out,
                })
            else:
                process_record = self.search([
                    ('device_id', '=', record.device_id.id),
                    ('employee_id', '=', record.mapped_employee_id.id),
                    ('check_in', '>=', date_str + ' 00:00:00'),
                    ('check_in', '<=', date_str + ' 23:59:59')
                ], limit=1)
                if record.check_status == 'check_in' and not process_record.check_in:
                    process_record.check_in = record.timestamp
                elif record.check_status == 'check_out' and not process_record.check_out:
                    process_record.check_out = record.timestamp