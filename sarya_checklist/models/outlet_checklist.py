from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime
from datetime import timedelta

class OutletChecklist(models.Model):
    _name = 'outlet.checklist'
    _description = 'Outlet Checklist'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True)
    config_id = fields.Many2one('checklist.config', required=True)
    outlet_id = fields.Many2one('pos.config', required=True)

    responsible_user_ids = fields.Many2many(
        'res.users', tracking=True
    )

    state = fields.Selection([
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')
    ], default='new', tracking=True)

    valid_till = fields.Datetime()
    completed_on = fields.Datetime()
    completed_by = fields.Many2one('res.users')

    line_ids = fields.One2many(
        'outlet.checklist.line', 'checklist_id'
    )
    is_expired = fields.Boolean(
        string="Expired",
        compute='_compute_is_expired',
        store=True
    )


    @api.depends('valid_till', 'state')
    def _compute_is_expired(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.is_expired = rec.valid_till and rec.valid_till < now and rec.state != 'completed'

    def action_start(self):
        now = fields.Datetime.now()
        for checklist in self:
            if checklist.valid_till and now > checklist.valid_till:
                raise UserError("Cannot start this checklist because it has expired.")
            checklist.state = 'in_progress'
            checklist.message_post(body="Checklist started")

    def action_complete(self):
        now = fields.Datetime.now()
        for checklist in self:
            if checklist.valid_till and now > checklist.valid_till:
                raise UserError("Cannot complete this checklist because it has expired.")

            # Check mandatory attachments
            for line in checklist.line_ids:
                if line.attachment_required and not line.attachment_ids:
                    raise UserError(
                        f"Line '{line.name}' requires attachments before completing the checklist."
                    )

            checklist.write({
                'state': 'completed',
                'completed_on': now,
                'completed_by': self.env.user.id
            })
            checklist.message_post(body="Checklist completed")




class OutletChecklistLine(models.Model):
    _name = 'outlet.checklist.line'
    _description = 'Outlet Checklist Line'

    checklist_id = fields.Many2one(
        'outlet.checklist', required=True, ondelete='cascade'
    )

    sequence = fields.Integer(default=10)

    display_type = fields.Selection([
        ('section', 'Section'),
        ('line', 'Checklist Line'),
        ('note', 'Note')
    ])

    name = fields.Char("Description")

    is_done = fields.Boolean()
    attachment_required = fields.Boolean("Attachment Mandatory")
    remark = fields.Text("Remark")

    attachment_ids = fields.Many2many(
        'ir.attachment', string="Attachments"
    )