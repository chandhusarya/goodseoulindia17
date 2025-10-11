from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError


class Contract(models.Model):
    _inherit = 'hr.contract'

    basic_percentage = fields.Float(
        string='Basic Percentage(%))', digits='Payroll', help='40% to 50% of CTC', default=50)
    basic = fields.Float(
        string='Basic', digits='Payroll')
    conveyance_allowance = fields.Float(
        string='Conveyance Allowance', digits='Payroll', default=1500, help='Fixed')
    pf_employee = fields.Float(
        string='PF- Employee Contribution', digits='Payroll', help='12% of the basic salary and DA')
    hr_allowance = fields.Float(
        string='HR Allowance', digits='Payroll')
    special_allowance = fields.Float(
        string='Special Allowance', digits='Payroll')
    pf_employee_employer = fields.Float(
        string='PF Employer Contribution')
    professional_tax = fields.Float(
        string='Professional TAX', digits='Payroll', default=200)
    total_ctc = fields.Float(
        string='Total CTC', digits='Payroll')
    total_deduction = fields.Float(
        string='Total Deduction', digits='Payroll')
    net_salary = fields.Float(
        string='Net Salary')
    l10n_in_house_rent_allowance_metro_nonmetro = fields.Float(string='House Rent Allowance (%)', digits='Payroll',
                                                               default=21, help='HRA is an allowance given by the employer to the employee for taking care of his rental or accommodation expenses for metro city it is 50% and for non metro 40%. \nHRA computed as percentage(%)')

    esic_employer = fields.Float(string='ESIC Employer')
    esic_employee = fields.Float(string='ESIC Employee')
    total_annual_ctc = fields.Float(string='Total Annual CTC')
    total_annual_deduction = fields.Float(string='Total Annual Deduction')
    total_annual_net_salary = fields.Float(string='Total Net Salary')
    total_annual_basic = fields.Float(string='Total Basic')
    total_annual_hr_allowance = fields.Float(string='Total Hr Allowance')
    total_annual_special_allowance = fields.Float(string='Total Special Allowance')
    total_annual_conveyance_allowance = fields.Float(string='Total Conveyance Allowance')
    total_annual_gratuity = fields.Float(string='Total Gratuity')
    total_annual_pf_employer_contribution = fields.Float(string='Total PF Employer Contribution')
    total_annual_esic_employer = fields.Float(string='Total Esic Employer')
    total_annual_pf_employee_contribution = fields.Float(string='Total PF Employee Contribution')
    total_annual_professional_tax = fields.Float(string='Total Professional TAX')
    total_annual_tds = fields.Float(string='Total TDS')
    total_annual_esic_employee = fields.Float(string='Total ESIC Employee')
    tax_config_id = fields.Many2one(
        'hr.tax.config',
        string='Tax Slab Regime'
    )
    contract_change_reason = fields.Selection([
        ('termination', 'Termination (No Renew)'),
        ('resignation', 'Resignation (No Renew)'),
        ('appraisal', 'Appraisal/Promotion (Renew)')], string="Contract Change Reason", copy=False, tracking=True)
    is_contract_updated = fields.Boolean(string="Is Contract Updated")


    def compute_agreed_salary(self):
        if self.wage > 0:
            # self.basic = self.wage * self.basic_percentage * .01
            self.hr_allowance = self.l10n_in_house_rent_allowance_metro_nonmetro * self.wage * .01
            self.pf_employee = self.basic * .12
            self.pf_employee_employer = self.basic * .12
            self.l10n_in_gratuity = self.basic * .0354
            self.professional_tax = 200
            self.onchange_allowance_deductions()


    def compute_net_salary(self):
        for contract in self:
            if contract.total_ctc < 1:
                raise ValidationError('Please input valid CTC amount')
            # if not contract.tax_config_id:
            #     raise ValidationError('Please Select Tax Slab Regime')

            total = 0
            #Baisc 50% of CTC
            basic = (contract.total_ctc * 50)/100
            contract.basic = basic
            total += basic

            #HRA 25% of CTC
            hra = (contract.total_ctc * 25)/100
            contract.hr_allowance = hra
            total += hra

            #Gratuity 1.77% of CTC
            gratuity = (contract.total_ctc * 1.77)/100
            contract.l10n_in_gratuity = gratuity
            total += gratuity

            #PF employeer 6% of CTC
            pf_employee_employer = (contract.total_ctc * 6)/100
            contract.pf_employee_employer = pf_employee_employer
            total += pf_employee_employer



            if contract.conveyance_allowance > 0:
                total += contract.conveyance_allowance


            print("\n\n\ntotal =====>> ", total)

            #Special Allowance = CTC - Total
            special_allowance = contract.total_ctc - total
            contract.special_allowance = special_allowance



            total_deduction = 0
            # PF employee 6% of CTC
            pf_employee = (contract.total_ctc * 6) / 100
            contract.pf_employee = pf_employee
            total_deduction += pf_employee_employer

            if contract.professional_tax > 0:
                total_deduction += contract.professional_tax


            #TDS is CTC - Total deduction
            ctc_deduction_diff = contract.total_ctc - total_deduction

            net_salary = ctc_deduction_diff - (gratuity + pf_employee_employer)

            if net_salary <= 21000:
                #ESIC Employer -  3.25%
                esic_employer = (net_salary * 3.25)/100
                total += esic_employer
                contract.esic_employer = esic_employer

                # ESIC Employee - .75%
                esic_employee = (net_salary * 0.75) / 100
                total_deduction += esic_employee
                contract.esic_employee = esic_employee

            # contract.net_salary = net_salary

            contract.write({
                'total_annual_ctc': contract.total_ctc * 12,
                # 'total_annual_deduction': contract.total_deduction * 12,
                # 'total_annual_net_salary': contract.net_salary * 12,
                'total_annual_basic': contract.basic * 12,
                'total_annual_hr_allowance': contract.hr_allowance * 12,
                'total_annual_special_allowance': contract.special_allowance * 12,
                'total_annual_conveyance_allowance': contract.conveyance_allowance * 12,
                'total_annual_gratuity': contract.l10n_in_gratuity * 12,
                'total_annual_pf_employer_contribution': contract.pf_employee_employer * 12,
                'total_annual_esic_employer': contract.esic_employer * 12,
                'total_annual_pf_employee_contribution': contract.pf_employee * 12,
                'total_annual_professional_tax': contract.professional_tax * 12,
                # 'total_annual_tds': contract.l10n_in_tds * 12,
                'total_annual_esic_employee': contract.esic_employee * 12,
            })

            annual_tds = 0.0
            monthly_tds = 0.0
            if contract.tax_config_id:
                monthly_tds, annual_tds = contract.compute_tds(contract.tax_config_id)
                contract.l10n_in_tds = monthly_tds
                total_deduction += monthly_tds

            contract.total_deduction = total_deduction
            contract.net_salary = net_salary - monthly_tds
            contract.total_annual_tds = contract.l10n_in_tds * 12
            contract.total_annual_deduction = contract.total_deduction * 12
            contract.total_annual_net_salary = contract.net_salary * 12

    def compute_ctc_from_net_salary(self):
        for contract in self:
            if contract.net_salary < 1:
                raise ValidationError('Please input a valid Net Salary amount')
            # if not contract.tax_config_id:
            #     raise ValidationError('Please Select Tax Slab Regime')
            ctc = (contract.net_salary + contract.professional_tax + contract.l10n_in_tds) / 0.8623

            print("\n\n\n\n=================================CTC")

            print("ctc =======>> ", ctc)

            print("\n\n\n")

            contract.total_ctc = ctc
            contract.compute_net_salary()


    def compute_ctc_from_net_salary_old(self):
        for contract in self:
            if contract.net_salary < 1:
                raise ValidationError('Please input a valid Net Salary amount')

            # Reverse deductions
            pf_employee_employer = (contract.total_ctc * 6) / 100
            gratuity = (contract.total_ctc * 1.77) / 100
            total_deduction = pf_employee_employer

            if contract.professional_tax > 0:
                total_deduction += contract.professional_tax

            # Reverse TDS
            tds = contract.net_salary + gratuity + pf_employee_employer
            contract.l10n_in_tds = tds

            # Reverse Total CTC Calculation
            contract.total_ctc = tds + total_deduction

            # Compute components
            contract.basic = (contract.total_ctc * 50) / 100
            contract.hr_allowance = (contract.total_ctc * 25) / 100
            contract.l10n_in_gratuity = (contract.total_ctc * 1.77) / 100
            contract.pf_employee_employer = (contract.total_ctc * 6) / 100

            total = (
                    contract.basic +
                    contract.hr_allowance +
                    contract.l10n_in_gratuity +
                    contract.pf_employee_employer
            )

            if contract.conveyance_allowance > 0:
                total += contract.conveyance_allowance

            contract.special_allowance = contract.total_ctc - total

            # Compute total deductions
            contract.pf_employee = (contract.total_ctc * 6) / 100
            contract.total_deduction = total_deduction

            # Assign net salary
            contract.net_salary = contract.l10n_in_tds - (contract.l10n_in_gratuity + contract.pf_employee_employer)



    def compute_annual_ctc_salary(self):
        for contract in self:
            if contract.total_annual_net_salary < 1:
                raise ValidationError('Please input a valid Annual Net Salary amount')
            # if not contract.tax_config_id:
            #     raise ValidationError('Please Select Tax Slab Regime')
            ctc = (contract.total_annual_net_salary + contract.total_annual_professional_tax + contract.total_annual_tds) / 0.8623
            contract.total_annual_ctc = ctc
            contract.compute_annual_net_salary()

    def compute_annual_net_salary(self):
        for contract in self:
            if contract.total_annual_ctc < 1:
                raise ValidationError('Please input valid Annual CTC amount')
            # if not contract.tax_config_id:
            #     raise ValidationError('Please Select Tax Slab Regime')

            total = 0
            #Baisc 50% of CTC
            basic = (contract.total_annual_ctc * 50)/100
            contract.total_annual_basic = basic
            total += basic

            #HRA 25% of CTC
            hra = (contract.total_annual_ctc * 25)/100
            contract.total_annual_hr_allowance = hra
            total += hra

            #Gratuity 1.77% of CTC
            gratuity = (contract.total_annual_ctc * 1.77)/100
            contract.total_annual_gratuity = gratuity
            total += gratuity

            #PF employeer 6% of CTC
            pf_employee_employer = (contract.total_annual_ctc * 6)/100
            contract.total_annual_pf_employer_contribution = pf_employee_employer
            total += pf_employee_employer



            if contract.total_annual_conveyance_allowance > 0:
                total += contract.total_annual_conveyance_allowance


            print("\n\n\ntotal =====>> ", total)

            #Special Allowance = CTC - Total
            special_allowance = contract.total_annual_ctc - total
            contract.total_annual_special_allowance = special_allowance



            total_deduction = 0
            # PF employee 6% of CTC
            pf_employee = (contract.total_annual_ctc * 6) / 100
            contract.total_annual_pf_employee_contribution = pf_employee
            total_deduction += pf_employee_employer

            if contract.total_annual_professional_tax > 0:
                total_deduction += contract.total_annual_professional_tax

            annual_tds = 0.0
            monthly_tds = 0.0
            if contract.tax_config_id:
                monthly_tds, annual_tds = contract.compute_tds(contract.tax_config_id)
                contract.total_annual_tds = annual_tds
                total_deduction += annual_tds

            contract.total_annual_deduction = total_deduction

            #TDS is CTC - Total deduction
            ctc_deduction_diff = contract.total_annual_ctc - total_deduction

            net_salary = ctc_deduction_diff - (gratuity + pf_employee_employer)

            if net_salary <= 252000:
                #ESIC Employer -  3.25%
                esic_employer = (net_salary * 3.25)/100
                total += esic_employer
                contract.total_annual_esic_employer = esic_employer

                # ESIC Employee - .75%
                esic_employee = (net_salary * 0.75) / 100
                total_deduction += esic_employee
                contract.total_annual_esic_employee = esic_employee

            contract.total_annual_net_salary = net_salary
            contract.total_ctc = contract.total_annual_ctc / 12
            contract.total_deduction = total_deduction / 12
            contract.net_salary = net_salary / 12
            contract.basic = basic / 12
            contract.hr_allowance = hra / 12
            contract.special_allowance = special_allowance / 12
            contract.conveyance_allowance = contract.total_annual_conveyance_allowance / 12
            contract.l10n_in_gratuity = gratuity / 12
            contract.pf_employee_employer = pf_employee_employer / 12
            contract.esic_employer = contract.total_annual_esic_employer / 12
            contract.pf_employee = pf_employee_employer / 12
            contract.professional_tax = contract.total_annual_professional_tax / 12
            contract.esic_employee = contract.total_annual_esic_employee / 12
            contract.l10n_in_tds = monthly_tds
            contract.esic_employee = contract.total_annual_esic_employee / 12

    def compute_tds(self, tax_config):
        monthly_tds = 0.0
        annual_tds = 0.0
        for contract in self:
            income = contract.total_annual_ctc
            taxable_income = income - tax_config.standard_deduction
            if taxable_income < tax_config.tax_rebate:
                monthly_tds = 0.0
                annual_tds = 0.0
            else:
                total_tax = 0.0
                # if rec.tax_config_id:
                for slab in tax_config.line_ids.sorted(lambda l: l.lower_limit):
                    lower = slab.lower_limit
                    upper = slab.upper_limit if slab.upper_limit > 0 else taxable_income
                    if taxable_income > lower:
                        taxable_amount = min(taxable_income, upper) - lower
                        total_tax += taxable_amount * (slab.rate / 100.0)
                monthly_tds = round(total_tax / 12, 2)
                annual_tds = round(total_tax, 2)
                health_education_cess_monthly = monthly_tds * (4 / 100.0)
                health_education_cess_yearly = annual_tds * (4 / 100.0)
                monthly_tds += health_education_cess_monthly
                annual_tds += health_education_cess_yearly
        return monthly_tds, annual_tds

    def action_open_survey(self):
        """Open the full survey form view"""
        self.ensure_one()
        employee_declaration_form = self.env.ref('sarya_hr.employee_declaration_survey_form')
        # if not self.declaration_form_id:
        #     raise UserError("Please select the Employee Declaration Form first.")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Employee Declaration Survey',
            'res_model': 'survey.survey',
            'view_mode': 'form',
            'res_id': employee_declaration_form.id,
            'target': 'current',
        }

    def action_view_filtered_participants(self):
        """Show participants for this employee only"""
        self.ensure_one()
        # if not self.declaration_form_id:
        #     raise UserError("Please select the Employee Declaration Form first.")
        employee_declaration_form = self.env.ref('sarya_hr.employee_declaration_survey_form')
        partner = self.employee_id.user_id.partner_id
        if not partner:
            raise UserError("Employee does not have a linked partner.")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Employee Survey Responses',
            'res_model': 'survey.user_input',
            'view_mode': 'tree,form',
            'domain': [
                ('survey_id', '=', employee_declaration_form.id),
                ('partner_id', '=', partner.id),
            ],
        }

    def action_terminate_contract(self):
        """ Open wizard to set termination date """
        return {
            "type": "ir.actions.act_window",
            "res_model": "terminate.contract.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_contract_id": self.id},
        }

    def action_renew_contract(self):
        """ Open wizard to renew contract """
        return {
            "type": "ir.actions.act_window",
            "res_model": "renew.contract.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_contract_id": self.id,
                        "default_net_salary": self.net_salary,
                        "default_ctc_salary": self.total_ctc,
                        "default_annual_net_salary": self.total_annual_net_salary,
                        "default_annual_ctc_salary": self.total_annual_ctc}
        }

    def action_compute_tds(self):
        if self.total_annual_ctc:
            self.compute_annual_net_salary()
        if self.total_ctc:
            self.compute_net_salary()




















    # @api.onchange('basic', 'hr_allowance', 'conveyance_allowance', 'special_allowance', 'conveyance_allowance', 'pf_employee', 'pf_employee_employer', 'l10n_in_gratuity', 'professional_tax')
    # def onchange_allowance_deductions(self):
    #     self.total_ctc = self.basic + self.conveyance_allowance + self.hr_allowance + self.special_allowance + self.pf_employee
    #     self.total_deduction = self.pf_employee + self.professional_tax
    #     self.net_salary = ((self.basic + self.conveyance_allowance + self.hr_allowance + self.special_allowance + self.pf_employee)
    #                        - (self.pf_employee_employer + self.professional_tax))
    #     self.wage = self.net_salary


