# models/hr_payslip.py
from odoo import models, fields, api

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _get_department_analytic_account(self):
        """Fetch the analytic account from the employee's department."""
        print('self.employee_id.department_id', self.employee_id.department_id.name)
        print('self.employee_id.department_id', self.employee_id.department_id.company_id)
        return self.employee_id.department_id.analytic_account_id

    def _get_employee_analytic_accounts(self):
        """Fetch the analytic accounts from the employee's record."""
        print('self.employee_id', self.employee_id.name)
        return self.employee_id.analytic_account_ids

    def _get_analytic_accounts_for_line(self, line):
        """Return combined analytic accounts for the payslip line."""
        analytic_accounts = {}
        emp_analytic_accounts = {}
        dept_analytic_accounts = {}
        employee_accounts = self._get_employee_analytic_accounts() or self.env['account.analytic.account']
        department_account = self._get_department_analytic_account()
        if employee_accounts:
            print('employee_accounts', employee_accounts)
            emp_analytic_accounts = {acc.id: 100/len(employee_accounts) for acc in employee_accounts}
            print('emp_analytic_accounts', emp_analytic_accounts)
        if department_account:
            dept_analytic_accounts = {acc.id: 100 for acc in department_account}
        analytic_accounts = {**emp_analytic_accounts, **dept_analytic_accounts}
        return analytic_accounts

    def _prepare_line_values(self, line, quantity, amount, rate, date):
        """Prepare line values with analytic accounts."""
        res = super(HrPayslip, self)._prepare_line_values(line, quantity, amount, rate, date)
        if line.salary_rule_id.use_analytic_account:
            analytic_accounts = self._get_analytic_accounts_for_line(line)
            if analytic_accounts:
                res['analytic_distribution'] = analytic_accounts
        return res

    def action_payslip_done(self):
        """Override to ensure analytic accounts are added to journal entries."""
        res = super(HrPayslip, self).action_payslip_done()
        for slip in self:
            for move in slip.move_id:
                for line in move.line_ids:
                    salary_rule = slip.line_ids.filtered(lambda l: l.salary_rule_id and (l.salary_rule_id.account_debit == line.account_id or l.salary_rule_id.account_credit == line.account_id)).salary_rule_id
                    if not line.analytic_distribution and salary_rule and salary_rule.use_analytic_account:
                        analytic_accounts = slip._get_analytic_accounts_for_line(line)
                        print("??????????????????????????????????",analytic_accounts)
                        if analytic_accounts:
                            line.analytic_distribution = {acc: 100 / len(analytic_accounts) for acc in analytic_accounts}
        return res

class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    use_analytic_account = fields.Boolean(string="Use Analytic Account", help="Enable analytic account tracking for this salary rule.")
