from odoo import models, fields
from datetime import timedelta

class ChecklistConfig(models.Model):
    _name = 'checklist.config'
    _description = 'Checklist Configuration'

    name = fields.Char(required=True)
    outlet_ids = fields.Many2many('pos.config', string="Outlets")

    frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly')
    ], required=True)

    validity_hours = fields.Integer(required=True)
    last_generated_on = fields.Datetime(readonly=True)

    responsible_master_id = fields.Many2one(
        'checklist.responsible.master', required=True
    )
    line_ids = fields.One2many(
        'checklist.config.line',
        'config_id',
        string="Checklist Lines"
    )


    def _create_outlet_checklist_lines(self, outlet_checklist):
        for line in self.line_ids:
            self.env['outlet.checklist.line'].create({
                'checklist_id': outlet_checklist.id,
                'sequence': line.sequence,
                'display_type': line.display_type,
                'name': line.name,
                'attachment_required': line.attachment_required,
            })

    def _is_due(self, config):
        """
        Check if the checklist config is due for generation based on frequency
        and last_generated_on.
        """
        if not config.last_generated_on:
            # Never generated before → it's due
            return True

        last = config.last_generated_on
        now = fields.Datetime.now()

        if config.frequency == 'daily':
            return now >= last + timedelta(days=1)
        elif config.frequency == 'weekly':
            return now >= last + timedelta(weeks=1)
        elif config.frequency == 'monthly':
            # Approximate monthly as 30 days
            return now >= last + timedelta(days=30)
        return False

    def _notify_user(self, user, checklist):
        """
        Send a push notification to the given user about the checklist.
        """
        checklist.message_post(
            body=f"You have been assigned to the checklist: <b>{checklist.name}</b>.",
            partner_ids=[user.partner_id.id],   # send to this user's partner
            message_type='notification',
        )

    def _cron_generate_outlet_checklists(self):
        configs = self.search([])
        now = fields.Datetime.now()

        for config in configs:
            if not self._is_due(config):
                continue
            for line in config.responsible_master_id.line_ids:
                checklist = self.env['outlet.checklist'].create({
                    'name': config.name,
                    'config_id': config.id,
                    'outlet_id': line.outlet_id.id,
                    'responsible_user_ids': line.user_ids,
                    'valid_till': now + timedelta(hours=config.validity_hours),
                })
                config._create_outlet_checklist_lines(checklist)
                for user in line.user_ids:
                    self._notify_user(user, checklist)

            config.last_generated_on = fields.Datetime.now()




class ChecklistConfigLine(models.Model):
    _name = 'checklist.config.line'
    _description = 'Checklist Config Line'
    _order = 'sequence, id'

    config_id = fields.Many2one(
        'checklist.config', required=True, ondelete='cascade'
    )

    sequence = fields.Integer(default=10)

    display_type = fields.Selection([
        ('section', 'Section'),
        ('line', 'Checklist Line'),
        ('note', 'Note')
    ], default='line')

    name = fields.Char("Title / Description")

    attachment_required = fields.Boolean()

    # UI helpers (same as sale.order.line)
    is_section = fields.Boolean(
        compute='_compute_is_section', store=False
    )

