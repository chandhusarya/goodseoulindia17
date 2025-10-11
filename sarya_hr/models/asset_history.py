from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AssetHistory(models.Model):
    _name = 'asset.history'
    _description = 'Asset History'
    _rec_name = 'employee_id'
    _inherit = ['mail.thread','mail.activity.mixin']

    employee_id = fields.Many2one('hr.employee', string="Taken By", copy=False, required=True)
    start_date = fields.Date("Allocation Date", copy=False, required=True)
    end_date = fields.Date("Return Date", copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('closed', 'Closed')], default='draft', string="Status", copy=False, tracking=True)
    asset_id = fields.Many2one('asset.master', string="Asset", copy=False, required=True)
    rtn_employee_id = fields.Many2one('hr.employee', string="Return By", copy=False)
    working_condition =  fields.Selection([('in','IN'),('out','OUT')])
    asset_category_id = fields.Many2one('asset.category', store=True, string="Asset Category",
                                        related='asset_id.asset_category_id')
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company', default=lambda self: self.env.company)

    def compute_is_approver(self):
        for rec in self:
            rec.is_approver = rec.show_approval_buttons()



    @api.depends('state')
    def action_running(self):
        for rec in self:
            if self.asset_id.is_allocated == True:
                raise UserError(_("%s is Already Allocated")%(self.asset_id.name))
            if rec.state == 'draft':
                rec.write({
                    'state': 'running'
                })
                rec.asset_id.is_allocated = True

    @api.depends('state')
    def action_closed(self):
        for rec in self:
            if rec.state == 'running':
                rec.asset_id.is_allocated = False
                rec.write({
                    'state': 'closed'
                })
