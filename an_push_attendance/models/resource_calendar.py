from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'



    fp_status_policy_id = fields.Many2one('fp.status.policy', string='Fingerprint Status Policy',)
    start_in = fields.Float()
    end_in = fields.Float()
    start_out = fields.Float()
    end_out = fields.Float()

    start_period = fields.Float(string='Start Period', help="Start of acceptable attendance period")
    end_period = fields.Float(string='End Period', help="End of acceptable attendance period")

    @api.constrains('start_period', 'end_period')
    def _check_period_values(self):
        for record in self:
            if not (0 <= record.start_period <= 24 and 0 <= record.end_period <= 27):
                raise ValidationError(
                    "Period values must be valid times (0-24 for start, 0-27 for end to handle after midnight)")



    @api.onchange('start_in')
    def change_start_in(self):
        self.attendance_ids.update({'start_in':self.start_in})
    @api.onchange('end_in')
    def change_end_in(self):
        self.attendance_ids.update({'end_in':self.end_in})
    @api.onchange('start_out')
    def change_start_out(self):
        self.attendance_ids.update({'start_out':self.start_out})
    @api.onchange('end_out')
    def change_end_out(self):
        self.attendance_ids.update({'end_out':self.end_out})


class ResourceCalendarAttendance(models.Model):
    _inherit = 'resource.calendar.attendance'

    start_in = fields.Float(string='Start In', digits=(16, 2), widget='float_time')
    end_in = fields.Float(string='End In', digits=(16, 2), widget='float_time')
    start_out = fields.Float(string='Start Out', digits=(16, 2), widget='float_time')
    end_out = fields.Float(string='End Out', digits=(16, 2), widget='float_time')

    start_period = fields.Float(string='Start Period', widget='float_time', help="Start of acceptable attendance period for this shift")
    end_period = fields.Float(string='End Period', widget='float_time', help="End of acceptable attendance period for this shift")

    @api.constrains('start_period', 'end_period')
    def _check_period_values(self):
        for record in self:
            if not (0 <= record.start_period <= 24 and 0 <= record.end_period <= 27):
                raise ValidationError(
                    "Period values must be valid times (0-24 for start, 0-27 for end to handle after midnight)")


    @api.constrains('start_in', 'end_in', 'start_out', 'end_out')
    def _check_hour_values(self):
        for record in self:
            if not (0 <= record.start_in < 24 and 0 <= record.end_in < 24 and 0 <= record.start_out < 24 and 0 <= record.end_out < 24):
                raise ValidationError("Time values must be between 00:00 and 23:59:59.")

    @api.onchange('hour_from', 'hour_to')
    def _onchange_hours(self):
        for record in self:
            if not record.start_period:
                record.start_period = record.hour_from
            if not record.end_period:
                record.end_period = record.hour_to
