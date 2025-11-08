from odoo import models, fields, api

class FingerprintTemplate(models.Model):
    _name = 'fingerprint.template'
    _description = 'Fingerprint Template'

    device_id = fields.Many2one('attendance.device', string='Device', required=True)
    user_id = fields.Many2one('device.user', string='User', required=True, ondelete='cascade',)
    fid = fields.Integer(string='Fingerprint ID')
    size = fields.Integer(string='Size')
    valid = fields.Boolean(string='Valid')
    template = fields.Text(string='Template')
    _sql_constraints = [
        ('unique_device_user_fid',
         'UNIQUE(device_id, user_id, fid)',
         'Fingerprint template with this FID already exists for this user!'),
    ]