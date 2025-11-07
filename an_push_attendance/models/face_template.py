from odoo import models, fields, api
from odoo.exceptions import ValidationError


class FaceTemplate(models.Model):
    _name = 'face.template'
    _description = 'Face Template'
    _order = 'device_id, user_id, fid'

    device_id = fields.Many2one('attendance.device', string='Device', required=True)
    user_id = fields.Many2one('device.user', string='User', required=True, ondelete='cascade')
    fid = fields.Integer(string='Face ID')
    size = fields.Integer(string='Size')
    valid = fields.Boolean(string='Valid')
    template = fields.Text(string='Template')
    active = fields.Boolean(default=True)

    # Add status field to track template state
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived')
    ], default='draft', string='Status')

    # Add template version tracking
    version = fields.Integer(string='Version', default=1)
    last_update = fields.Datetime(string='Last Updated')

    _sql_constraints = [
        ('unique_device_user_fid_active',
         'UNIQUE(device_id, user_id, fid, active)',
         'Active face template with this FID already exists for this user!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        # Process each vals dict to archive existing templates and set last_update
        for vals in vals_list:
            # Archive existing templates with same FID
            existing = self.search([
                ('device_id', '=', vals.get('device_id')),
                ('user_id', '=', vals.get('user_id')),
                ('fid', '=', vals.get('fid')),
                ('active', '=', True)
            ])
            if existing:
                existing.write({
                    'active': False,
                    'state': 'archived'
                })
            
            # Set last_update
            vals['last_update'] = fields.Datetime.now()
            
        return super().create(vals_list)

    def write(self, vals):
        if 'template' in vals:
            vals['version'] = self.version + 1
            vals['last_update'] = fields.Datetime.now()
        return super(FaceTemplate, self).write(vals)

    def archive_template(self):
        self.ensure_one()
        self.write({
            'active': False,
            'state': 'archived'
        })

    def activate_template(self):
        self.ensure_one()
        # Deactivate other templates with same FID
        self.search([
            ('device_id', '=', self.device_id.id),
            ('user_id', '=', self.user_id.id),
            ('fid', '=', self.fid),
            ('id', '!=', self.id),
            ('active', '=', True)
        ]).write({
            'active': False,
            'state': 'archived'
        })

        self.write({
            'active': True,
            'state': 'active'
        })