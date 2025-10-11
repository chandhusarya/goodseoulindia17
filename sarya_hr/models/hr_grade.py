from odoo import fields, models, api


class HrGrade(models.Model):
    _name = 'hr.grade'
    _description = 'Employee Grade'

    name = fields.Char()
    job_positions = fields.One2many(
        comodel_name='hr.job',
        inverse_name='grade_id',
        string='Job Positions')
