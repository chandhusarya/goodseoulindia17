from odoo import fields, models, api


class HrJob(models.Model):
    _inherit = 'hr.job'

    grade_id = fields.Many2one('hr.grade', string='Grade')
