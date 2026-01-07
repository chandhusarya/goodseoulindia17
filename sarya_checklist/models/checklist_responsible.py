from odoo import models, fields

class ChecklistResponsibleMaster(models.Model):
    _name = 'checklist.responsible.master'
    _description = 'Checklist Responsible Master'

    name = fields.Char(required=True)
    line_ids = fields.One2many(
        'checklist.responsible.line', 'master_id'
    )
    notify_user_ids = fields.Many2many(
        'res.users',
        string="Notify Users",
        help="User who will receive notification email when checklist is completed."
    )


class ChecklistResponsibleLine(models.Model):
    _name = 'checklist.responsible.line'
    _description = 'Checklist Responsible Line'

    master_id = fields.Many2one(
        'checklist.responsible.master', required=True
    )

    outlet_id = fields.Many2one(
        'pos.config', required=True
    )

    user_ids = fields.Many2many('res.users')
