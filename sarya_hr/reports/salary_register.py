# models/hr_payslip_batch.py
from odoo import models, fields
import xlsxwriter
import io

class HrPayslipBatch(models.Model):
    _inherit = 'hr.payslip.run'


    # Excel Report Generation
    excel_file_name = fields.Char('Excel File Name')
    excel_file = fields.Binary("Excel File")


    def action_print_salary_register(self):
        # Create Excel workbook
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet = workbook.add_worksheet('Salary Register')

        # Define styles
        bold = workbook.add_format({'bold': True, 'bg_color': '#99CCFF'})
        amount_format = workbook.add_format({'num_format': '#,##0.00'})
        highlight = workbook.add_format({'bg_color': '#FFD3B6'})

        # Header Info
        sheet.write('A1', 'Company Name:', bold)
        sheet.write('B1', self.company_id.name)
        sheet.write('A2', 'Salary Month', bold)
        sheet.write('B2', self.name)
        sheet.write('A3', 'Total Number of Employees', bold)
        sheet.write('B3', len(self.slip_ids))

        # Table Header
        headers = [
            'Employee Code', 'Employee Name', 'Date of Joining', 'Attendance', 'Basic Salary', 'HRA',
            'Special Allowance', 'Conveyance Allowance', 'Gratuity', 'PF Employer', 'ESIC Employer', 'Gross Salary',
            'PF Employee', 'ESIC Employee', 'TDS', 'Net Salary Payable'
        ]

        for col, header in enumerate(headers):
            sheet.write(4, col, header, bold)

        # Data Rows
        row = 5
        for payslip in self.slip_ids:
            sheet.write(row, 0, '')
            sheet.write(row, 1, payslip.employee_id.name)
            sheet.write(row, 2, payslip.employee_id.first_contract_date.strftime('%d-%m-%Y') if payslip.employee_id.first_contract_date else '')
            print("payslip.worked_days_line_ids.mapped('number_of_days')", sum(payslip.worked_days_line_ids.mapped('number_of_days')))
            sheet.write(row, 3, sum(payslip.worked_days_line_ids.mapped('number_of_days')), amount_format)

            # Fetching salary components
            def get_amount(code):
                return sum(payslip.line_ids.filtered(lambda l: l.code == code).mapped('total'))

            sheet.write(row, 4, get_amount('BASIC'), amount_format)
            sheet.write(row, 5, get_amount('HRA'), amount_format)
            sheet.write(row, 6, get_amount('SPL'), amount_format)
            sheet.write(row, 7, get_amount('CON'), amount_format)
            sheet.write(row, 8, get_amount('GRA'), amount_format)
            sheet.write(row, 9, get_amount('PFE'), amount_format)
            sheet.write(row, 10, get_amount('ESICEMP'), amount_format)
            amount = get_amount('BASIC') + get_amount('HRA') + get_amount('SA') + get_amount('CA') + get_amount('GRATUITY') + get_amount('GRATUITY') + get_amount('ESICE')
            sheet.write(row, 11, get_amount('GROSS'), amount_format)

            # Employee Deductions
            sheet.write(row, 12, get_amount('PF'), amount_format)
            sheet.write(row, 13, get_amount('ESICD'), amount_format)
            sheet.write(row, 14, get_amount('TDS'), amount_format)

            # Net Salary Payable
            sheet.write(row, 15, get_amount('NET'), amount_format)

            row += 1

        workbook.close()
        output.seek(0)
        import base64
        generated_file = base64.b64encode(output.read())
        output.close()

        self.excel_file = generated_file
        self.excel_file_name = "Salary Register.xlsx"
        return {
            'name': 'SAL',
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=hr.payslip.run&id={}&field=excel_file&filename_field=excel_file_name&download=true'.format(
                self.id
            ),
            'target': 'self',
        }
