from odoo import fields, models, api


class EmployeeDocVerify(models.Model):
    _name = 'employee.doc.verify'
    _description = 'Employee Document Verify'

    name = fields.Char(default='New', readonly=True)
    l10n_in_uan = fields.Char(string='UAN')
    l10n_in_pan = fields.Char(string='PAN')
    l10n_in_esic_number = fields.Char(string='ESIC Number')
    pf_number = fields.Char('PF Number')
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        required=True)
    state = fields.Selection(
        string='Status',
        selection=[('pending', 'Pending'),
                   ('verified', 'Verified'), ], default='pending')
    verify_token = fields.Char(
        string='Verify Token')
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company', default=lambda self: self.env.company)



    @api.model
    def create(self, values):
        if self.env.company.company_type == 'retail':
            values['name'] = self.env['ir.sequence'].next_by_code('emp.doc.verify.seq.ret')
        if self.env.company.company_type == 'distribution':
            values['name'] = self.env['ir.sequence'].next_by_code('emp.doc.verify.seq.dist')
        return super(EmployeeDocVerify, self).create(values)

    def get_portal_url(self):
        self.ensure_one()
        url = '/employee/verify?access_token=%s'% (self.verify_token)
        return url
