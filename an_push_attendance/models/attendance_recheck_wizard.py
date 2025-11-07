from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime

class AttendanceRecheckWizard(models.TransientModel):
    _name = 'attendance.recheck.wizard'
    _description = 'Attendance Recheck Wizard'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    start_date = fields.Date(string='Start Date', required=True, default=fields.Date.context_today)
    end_date = fields.Date(string='End Date', required=True, default=fields.Date.context_today)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for wizard in self:
            if wizard.start_date > wizard.end_date:
                raise ValidationError('Start date must be before end date')

    def action_recheck_period(self):
        self.ensure_one()
        
        try:
            # Call the recheck_period method
            records_count = self.env['attendance.record'].recheck_period(
                self.employee_id.id,
                self.start_date,
                self.end_date
            )
            
            # Show success message
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': f'Successfully rechecked {records_count} records for {self.employee_id.name}',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise ValidationError(f"Error processing records: {str(e)}") 