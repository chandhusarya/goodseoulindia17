from odoo import models, fields, api


class DeviceUser(models.Model):
    _name = 'device.user'
    _description = 'Device User Info'

    device_id = fields.Many2one('attendance.device', string='Device', required=True)
    pin = fields.Char(string='PIN', required=True)
    name = fields.Char(string='Name')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    privilege = fields.Integer(string='Privilege')
    password = fields.Char(string='Password')
    card = fields.Char(string='Card')
    group = fields.Char(string='Group')
    time_zone = fields.Char(string='Time Zone')
    verify = fields.Integer(string='Verify')
    vice_card = fields.Char(string='Vice Card')
    post_data = fields.Text(string='POST Data', readonly=True)

    fingerprint_template_ids = fields.One2many('fingerprint.template', 'user_id', string='Fingerprint Templates')
    attendance_record_ids = fields.One2many('attendance.record', compute='_compute_attendance_records',
                                            string='Attendance Records')


    _sql_constraints = [
        ('unique_device_pin',
         'UNIQUE(device_id, pin)',
         'User with this PIN already exists on this device!'),
    ]


    @api.depends('pin')
    def _compute_attendance_records(self):
        for user in self:
            user.attendance_record_ids = self.env['attendance.record'].search([('pin', '=', user.pin)])

    def action_view_fingerprint_templates(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Fingerprint Templates',
            'view_mode': 'tree,form',
            'res_model': 'fingerprint.template',
            'domain': [('user_id', '=', self.id)],
            'context': "{'create': False}"
        }

    def action_view_attendance_records(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Attendance Records',
            'view_mode': 'tree,form',
            'res_model': 'attendance.record',
            'domain': [('pin', '=', self.pin)],
            'context': "{'create': False}"
        }

    def create_user_info(self, device, user_info, data):
        user_data = {}
        lines = data.split('\n')
        for line in lines:
            if '=' in line:
                key, value = line.split('=', 1)
                user_data[key.strip()] = value.strip()

        pin = user_data.get('PIN')
        if not pin:
            return

        existing_user = self.search([('device_id', '=', device.id), ('pin', '=', pin)], limit=1)
        if existing_user:
            existing_user.write({
                'name': user_data.get('Name'),
                'privilege': int(user_data.get('Privilege', 0)),
                'password': user_data.get('Password'),
                'card': user_data.get('Card'),
                'group': user_data.get('Group'),
                'time_zone': user_data.get('TimeZone'),
                'verify': int(user_data.get('Verify', 0)),
                'vice_card': user_data.get('ViceCard'),
                'post_data': user_info,
            })
        else:
            self.create({
                'device_id': device.id,
                'pin': pin,
                'name': user_data.get('Name'),
                'privilege': int(user_data.get('Privilege', 0)),
                'password': user_data.get('Password'),
                'card': user_data.get('Card'),
                'group': user_data.get('Group'),
                'time_zone': user_data.get('TimeZone'),
                'verify': int(user_data.get('Verify', 0)),
                'vice_card': user_data.get('ViceCard'),
                'post_data': user_info,
            })

    def map_device_users_to_employees(self):
        # IrConfigParam = self.env['ir.config_parameter']
        link = self.env['attendance.config.settings'].search([],limit=1)
        employee_link_field = link.employee_link_field if link else 'barcode'

        for user in self:
            if not user.employee_id:
                search_domain = [(employee_link_field, '=', user.pin)]
                employee = self.env['hr.employee'].search(search_domain, limit=1)
                if employee:
                    user.employee_id = employee

                    # Update attendance records
                    attendance_records = self.env['attendance.record'].search(
                        [('pin', '=', user.pin), ('device_id', '=', user.device_id.id)])
                    for record in attendance_records:
                        record.mapped_employee_id = employee
