from odoo import fields, models, api


class HrDepartment(models.Model):
    _inherit = 'hr.department'


    analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Analytic Account')
