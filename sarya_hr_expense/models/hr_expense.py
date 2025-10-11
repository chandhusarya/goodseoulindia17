from odoo import fields, models, api
from datetime import datetime
from odoo import api, fields, Command, models, _


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    exp_type = fields.Selection([('actual', 'Actual'),
                                ('advance', 'Advance')], string='Expense Type', tracking=True, default='actual')







class HrExpense(models.Model):
    _inherit = "hr.expense"

    exp_type = fields.Selection([('actual', 'Actual'),
                                ('advance', 'Advance')], string='Expense Type', tracking=True, default='actual')
    advance_amount = fields.Float(string="Advance Amount")


