from odoo import models, fields, api
from datetime import datetime, timedelta


class DeviceCommand(models.Model):
    _name = 'device.command'
    _description = 'Device Command'
    _order = 'create_date desc'

    device_id = fields.Many2one('attendance.device', string='Device', required=True)
    command = fields.Char(string='Command', required=True)
    status = fields.Selection([
        ('sent', 'Sent'),
        ('received', 'Received'),
        ('failed', 'Failed'),
        ('timeout', 'Timeout')
    ], string='Status', default='sent')
    result = fields.Text(string='Result')
    retry_count = fields.Integer(string='Retry Count', default=0)
    last_retry = fields.Datetime(string='Last Retry')
    timeout_minutes = fields.Integer(string='Timeout (minutes)', default=5)

    @api.model
    def create_command(self, device, command):
        # Check for existing pending command
        existing_command = self.search([
            ('device_id', '=', device.id),
            ('command', '=', command),
            ('status', '=', 'sent')
        ], limit=1)

        if existing_command:
            return existing_command

        return self.create({
            'device_id': device.id,
            'command': command,
            'status': 'sent',
        })

    def update_command(self, result, status):
        self.write({
            'result': result,
            'status': status,
        })

    @api.model
    def cleanup_old_commands(self):
        """Cleanup old commands periodically"""
        timeout_threshold = datetime.now() - timedelta(days=7)
        old_commands = self.search([
            ('create_date', '<', timeout_threshold),
            ('status', 'in', ['received', 'failed', 'timeout'])
        ])
        old_commands.unlink()

    @api.model
    def check_timeouts(self):
        """Check for timed out commands"""
        for command in self.search([('status', '=', 'sent')]):
            timeout_time = command.create_date + timedelta(minutes=command.timeout_minutes)
            if datetime.now() > timeout_time:
                command.write({
                    'status': 'timeout',
                    'result': 'Command timed out'
                })