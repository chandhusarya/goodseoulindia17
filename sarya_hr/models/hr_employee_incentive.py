from odoo import fields, models, api


class EmployeeIncentive(models.Model):
    _name = 'employee.incentive'
    _description = 'Employee Incentive'
    _inherit = ['mail.thread','mail.activity.mixin']

    name = fields.Char(default='New')
    date = fields.Date()
    state = fields.Selection(
        string='Status',
        selection=[('new', 'New'),
                   ('confirm', 'Confirmed'), ],)
    line_ids = fields.One2many(
        comodel_name='employee.incentive.lines',
        inverse_name='incentive_id',
        string='Line Ids')

        
    

class EmployeeIncentiveLines(models.Model):
    _name = 'employee.incentive.lines'
    _description = 'Employee Incentive Lines'

    name = fields.Char(name='Description')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    amount = fields.Float('Amount')
    incentive_id = fields.Many2one(
        comodel_name='employee.incentive',
        string='Incentive')