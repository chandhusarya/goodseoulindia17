from odoo import fields, models, api


class HRLeaveType(models.Model):
    _inherit = "hr.leave.type"

    days_calculation = fields.Selection(
        string='Days Calculation',
        selection=[('working', 'Working Days'),
                   ('calendar', 'Calendar Days'), ],
        required=True, default='working')
