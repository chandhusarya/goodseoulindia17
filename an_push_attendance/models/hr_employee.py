from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    fingerprint_no = fields.Char(string='Finger Print No', unique=True)
    fp_policy_ids = fields.Many2many('fp.status.policy', 'employee_policy_rel', 'employee_id', 'policy_id',
                                     string='Fingerprint Policies')

    _sql_constraints = [
        ('fingerprint_no_unique', 'unique(fingerprint_no)', 'The Finger Print No must be unique.'),
    ]


    def get_current_policy(self, date=None):
        """Get the current applicable policy for this employee"""
        return self.env['fp.status.policy'].get_active_policy(self.id, date)



    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        
        # Process fingerprint policies for each record
        for record, vals in zip(records, vals_list):
            if vals.get('fp_policy_ids'):
                policies = self.env['fp.status.policy'].browse(vals['fp_policy_ids'][0][2])
                for policy in policies:
                    if record.id not in policy.employee_ids.ids:
                        policy.write({'employee_ids': [(4, record.id)]})
                        
        return records

    def write(self, vals):
        result = super().write(vals)
        if 'fp_policy_ids' in vals:
            for employee in self:
                # Sync new policies
                for policy in employee.fp_policy_ids:
                    if employee.id not in policy.employee_ids.ids:
                        policy.write({'employee_ids': [(4, employee.id)]})

                # Remove from old policies
                old_policies = self.env['fp.status.policy'].search([
                    ('employee_ids', 'in', employee.id),
                    ('id', 'not in', employee.fp_policy_ids.ids)
                ])
                for policy in old_policies:
                    policy.write({'employee_ids': [(3, employee.id)]})
        return result