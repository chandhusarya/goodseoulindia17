from odoo import models, fields, api


class BiometricData(models.Model):
    _name = 'biometric.data'
    _description = 'Biometric Data'
    _order = 'create_date desc'

    device_id = fields.Many2one('attendance.device', string='Device', required=True, ondelete='cascade')
    user_id = fields.Many2one('device.user', string='User', required=True, ondelete='cascade')
    bio_type = fields.Char(string='Biometric Type', required=True)
    template = fields.Binary(string='Template', attachment=True)
    template_size = fields.Integer(string='Template Size')
    valid = fields.Boolean(string='Valid', default=True)
    create_date = fields.Datetime(string='Created On', readonly=True)
    write_date = fields.Datetime(string='Last Updated On', readonly=True)

    _sql_constraints = [
        ('unique_biometric_data',
         'UNIQUE(device_id, user_id, bio_type)',
         'Biometric data for this type already exists for this user!'),
    ]
    
    @api.model
    def get_bio_type_display(self):
        """Get user-friendly display for biometric type"""
        return {
            'FP': 'Fingerprint',
            'FACE': 'Face', 
            'FINGER': 'Fingerprint',
            'PALM': 'Palm',
            '0': 'Fingerprint #0',
            '1': 'Fingerprint #1',
            '2': 'Fingerprint #2',
            '3': 'Fingerprint #3',
            '4': 'Fingerprint #4',
            '5': 'Fingerprint #5',
            '6': 'Fingerprint #6',
            '7': 'Fingerprint #7',
            '8': 'Fingerprint #8',
            '9': 'Fingerprint #9',
        } 