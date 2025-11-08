from odoo import models, fields, api
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError

import pytz
import hashlib
import traceback
from odoo.http import request
import re



class AttendanceDevice(models.Model):
    _name = 'attendance.device'
    _description = 'Attendance Device'
    _inherit = ['mail.thread']

    # State management fields
    device_state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('inactive', 'Inactive')
    ], string='Device State', default='draft', tracking=True, required=True,
       help="Draft: Newly detected device, not yet fully configured\n"
            "Active: Device is operational and recording attendance\n"
            "Inactive: Device is temporarily disabled")
    
    active = fields.Boolean(string='Active', compute='_compute_active', store=True)
    
    @api.depends('device_state')
    def _compute_active(self):
        for device in self:
            device.active = device.device_state in ('draft', 'active')

    # Status and color fields for kanban view
    status = fields.Selection([
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('warning', 'Warning')
    ], string='Status', compute='_compute_device_status', store=True)
    
    # Flag for auto-created devices
    is_auto_created = fields.Boolean(string='Auto Created', default=False,
                                    help="This device was automatically created when it connected to Odoo")
    
    color = fields.Integer(string='Color', compute='_compute_device_status', store=True)
    
    @api.depends('last_handshake')
    def _compute_device_status(self):
        for device in self:
            if not device.last_handshake:
                device.status = 'offline'
                device.color = 1  # Red
            else:
                now = fields.Datetime.now()
                time_diff = now - device.last_handshake
                
                if time_diff <= timedelta(hours=1):
                    device.status = 'online'
                    device.color = 10  # Green
                elif time_diff <= timedelta(hours=24):
                    device.status = 'warning'
                    device.color = 3  # Yellow
                else:
                    device.status = 'offline'
                    device.color = 1  # Red

    # Existing fields
    name = fields.Char(string='Device Name', required=True)
    serial_number = fields.Char(string='Serial Number', required=True)
    location = fields.Many2one('hr.work.location', string='Location')
    response_value = fields.Text(string='Response Value')

    # New fields for device info
    device_name_info = fields.Char(string='Device Name', readonly=True)
    mac = fields.Char(string='MAC Address', readonly=True)
    transaction_count = fields.Integer(string='Transaction Count', readonly=True)
    fp_count = fields.Integer(string='Fingerprint Count', readonly=True)
    max_att_log_count = fields.Integer(string='Max Attendance Log Count', readonly=True)
    user_count = fields.Integer(string='User Count', readonly=True)
    max_user_count = fields.Integer(string='Max User Count', readonly=True)
    max_user_photo_count = fields.Integer(string='Max User Photo Count', readonly=True)
    platform = fields.Char(string='Platform', readonly=True)
    oem_vendor = fields.Char(string='OEM Vendor', readonly=True)
    fw_version = fields.Char(string='Firmware Version', readonly=True)
    push_version = fields.Char(string='Push Version', readonly=True)
    zkfp_version = fields.Char(string='ZKFP Version', readonly=True)
    ip_address = fields.Char(string='IP Address', readonly=True)
    max_face_count = fields.Integer(string='Max Face Count', readonly=True)
    device_type = fields.Selection([
        ('zk', 'ZKTeco'),
        ('essl', 'ESSL'),
        ('other', 'Other')
    ], string='Device Type', required=True, default='zk', 
       ondelete={'zk': 'set default', 'essl': 'set default', 'other': 'set default'})
    language = fields.Integer(string='Language', readonly=True)
    push_options_flag = fields.Integer(string='Push Options Flag', readonly=True)
    
    # ESSL specific fields
    photo_fun_on = fields.Boolean(string='Photo Function Enabled', readonly=True)
    finger_fun_on = fields.Boolean(string='Fingerprint Function Enabled', readonly=True)
    fp_version = fields.Char(string='Fingerprint Version', readonly=True)
    max_finger_count = fields.Integer(string='Max Fingerprint Count', readonly=True)
    face_fun_on = fields.Boolean(string='Face Function Enabled', readonly=True)
    face_version = fields.Char(string='Face Version', readonly=True)
    face_count = fields.Integer(string='Face Count', readonly=True)
    fv_fun_on = fields.Boolean(string='Face Verification Function Enabled', readonly=True)
    fv_version = fields.Char(string='Face Verification Version', readonly=True)
    max_fv_count = fields.Integer(string='Max Face Verification Count', readonly=True)
    fv_count = fields.Integer(string='Face Verification Count', readonly=True)
    pv_fun_on = fields.Boolean(string='Palm Verification Function Enabled', readonly=True)
    pv_version = fields.Char(string='Palm Verification Version', readonly=True)
    max_pv_count = fields.Integer(string='Max Palm Verification Count', readonly=True)
    pv_count = fields.Integer(string='Palm Verification Count', readonly=True)
    multi_bio_data_support = fields.Char(string='Multi Biometric Data Support', readonly=True)
    multi_bio_photo_support = fields.Char(string='Multi Biometric Photo Support', readonly=True)
    visilight_fun = fields.Boolean(string='Visible Light Function Enabled', readonly=True)
    ir_temp_detection_fun_on = fields.Boolean(string='IR Temperature Detection Enabled', readonly=True)
    mask_detection_fun_on = fields.Boolean(string='Mask Detection Enabled', readonly=True)
    user_pic_url_fun_on = fields.Boolean(string='User Picture URL Function Enabled', readonly=True)
    visual_intercom_fun_on = fields.Boolean(string='Visual Intercom Function Enabled', readonly=True)
    video_tid = fields.Char(string='Video TID', readonly=True)
    qr_code_decrypt_fun_list = fields.Char(string='QR Code Decrypt Function List', readonly=True)
    video_protocol = fields.Char(string='Video Protocol', readonly=True)
    is_support_qrcode = fields.Boolean(string='QR Code Support', readonly=True)
    qr_code_enable = fields.Boolean(string='QR Code Enabled', readonly=True)
    subcontracting_upgrade_fun_on = fields.Boolean(string='Subcontracting Upgrade Function Enabled', readonly=True)

    # Add log field for debugging
    last_request_params = fields.Text(string='Last Request Params', readonly=True)

    @api.model
    def _get_default_timezone(self):
        """
        Get the system's timezone from Odoo configuration
        """
        # First try to get from context
        context_tz = self.env.context.get('tz')
        if context_tz:
            return context_tz
            
        # Then try to get from user
        user_tz = self.env.user.tz
        if user_tz:
            return user_tz
            
        # Finally use server timezone from config or fallback to UTC
        server_tz = self.env['ir.config_parameter'].sudo().get_param('timezone')
        return server_tz or 'UTC'

    device_time_zone = fields.Selection(
        [(tz, tz) for tz in pytz.all_timezones],
        string='Device Time Zone',
        default=_get_default_timezone,
        required=True)

    # Fields for handshake response
    attlog_stamp = fields.Char(string='ATTLOG Stamp', default='None')
    operlog_stamp = fields.Char(string='OPERLOG Stamp', default='9999')
    attphoto_stamp = fields.Char(string='ATTPHOTO Stamp', default='None')
    error_delay = fields.Integer(string='Error Delay', default=30)
    delay = fields.Integer(string='Delay', default=10)
    trans_times = fields.Char(string='Trans Times', default='00:00;14:00')
    trans_interval = fields.Integer(string='Trans Interval', default=1)
    time_zone = fields.Integer(string='Time Zone', compute='_compute_time_zone')
    encrypt = fields.Char(string='Encrypt', default='None')
    server_ver = fields.Char(string='Server Version', default='2.4.1')
    table_name_stamp = fields.Char(string='Table Name Stamp', default='None')
    last_handshake = fields.Datetime(string='Last Handshake')

    # TransFlag checkboxes
    realtime = fields.Boolean(string='Realtime', default=True)
    trans_flag_transdata = fields.Boolean(string='TransData', default=True)
    trans_flag_attlog = fields.Boolean(string='AttLog', default=True)
    trans_flag_oplog = fields.Boolean(string='OpLog', default=True)
    trans_flag_attphoto = fields.Boolean(string='AttPhoto', default=True)
    trans_flag_enrolluser = fields.Boolean(string='EnrollUser', default=True)
    trans_flag_chguser = fields.Boolean(string='ChgUser', default=True)
    trans_flag_enrollfp = fields.Boolean(string='EnrollFP', default=True)
    trans_flag_chgfp = fields.Boolean(string='ChgFP', default=True)
    trans_flag_userpic = fields.Boolean(string='UserPic', default=True)

    # New field for barcode input
    barcode = fields.Char(string='Barcode')
    attendance_record_ids = fields.One2many('attendance.record', 'device_id', string='Attendance Records', readonly=True)

    command_count = fields.Integer(string='Command Count', compute='_compute_command_count')
    attendance_count = fields.Integer(string='Attendance Count', compute='_compute_attendance_count')
    fingerprint_template_count = fields.Integer(string='Fingerprint Template Count', compute='_compute_fingerprint_template_count')
    device_user_ids = fields.One2many('device.user', 'device_id', string='Device Users', readonly=True)
    operation_log_count = fields.Integer(string='Operation Logs', compute='_compute_operation_log_count')

    # New field for face templates
    face_template_ids = fields.One2many('face.template', 'device_id', string='Face Templates', readonly=True)
    face_template_count = fields.Integer(
        string='Face Templates',
        compute='_compute_face_template_count'
    )

    def unlink(self):
        # Check if any device is active
        for device in self:
            if device.active:
                raise ValidationError('You cannot delete an active device. Please archive it first.')
        # Delete related records first
        self.env['operation.log'].search([('device_id', 'in', self.ids)]).unlink()
        self.env['attendance.record'].search([('device_id', 'in', self.ids)]).unlink()
        self.env['device.command'].search([('device_id', 'in', self.ids)]).unlink()
        self.env['device.user'].search([('device_id', 'in', self.ids)]).unlink()
        self.env['fingerprint.template'].search([('device_id', 'in', self.ids)]).unlink()
        self.env['face.template'].search([('device_id', 'in', self.ids)]).unlink()
        self.env['user.picture'].search([('device_id', 'in', self.ids)]).unlink()
        return super(AttendanceDevice, self).unlink()

    picture_count = fields.Integer(
        compute='_compute_picture_count',
        string='Pictures'
    )

    def _compute_picture_count(self):
        for user in self:
            user.picture_count = self.env['user.picture'].search_count([
                ('user_id', '=', user.id),
                ('active', '=', True)
            ])

    def action_view_pictures(self):
        self.ensure_one()
        return {
            'name': 'User Pictures',
            'type': 'ir.actions.act_window',
            'res_model': 'user.picture',
            'view_mode': 'kanban,tree,form',
            'domain': [('user_id', '=', self.id), ('active', '=', True)],
            'context': {'default_user_id': self.id}
        }

    def _compute_face_template_count(self):
        for device in self:
            device.face_template_count = self.env['face.template'].search_count([
                ('device_id', '=', device.id)
            ])

    def action_view_face_templates(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Face Templates',
            'res_model': 'face.template',
            'view_mode': 'tree,form',
            'domain': [('device_id', '=', self.id)],
            'context': {'default_device_id': self.id}
        }

    @api.depends('device_time_zone')
    def _compute_time_zone(self):
        for device in self:
            if device.device_time_zone:
                tz = pytz.timezone(device.device_time_zone)
                device.time_zone = int(tz.utcoffset(datetime.now()).total_seconds() / 3600)
            else:
                device.time_zone = 3  # Assign a default value if device_time_zone is not set

    def _compute_command_count(self):
        for device in self:
            device.command_count = self.env['device.command'].search_count([('device_id', '=', device.id)])

    def _compute_attendance_count(self):
        for device in self:
            device.attendance_count = self.env['attendance.record'].search_count([('device_id', '=', device.id)])

    def _compute_fingerprint_template_count(self):
        for device in self:
            device.fingerprint_template_count = self.env['fingerprint.template'].search_count(
                [('device_id', '=', device.id)])

    def action_map_device_users(self):
        self.ensure_one()
        self.device_user_ids.map_device_users_to_employees()
        self.attendance_record_ids.map_device_users_to_employees()
        return True

    def action_view_device_users(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Device Users',
            'view_mode': 'tree,form',
            'res_model': 'device.user',
            'domain': [('device_id', '=', self.id)],
            'context': "{'create': False}"
        }

    def action_view_fingerprint_templates(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Fingerprint Templates',
            'view_mode': 'tree,form',
            'res_model': 'fingerprint.template',
            'domain': [('device_id', '=', self.id)],
            'context': "{'create': False}"
        }

    def action_view_device_commands(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Device Commands',
            'view_mode': 'tree,form',
            'res_model': 'device.command',
            'domain': [('device_id', '=', self.id)],
            'context': "{'create': False}"
        }

    def action_view_attendance_records(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Attendance Records',
            'view_mode': 'tree,form',
            'res_model': 'attendance.record',
            'domain': [('device_id', '=', self.id)],
            'context': "{'create': False}"
        }

    def process_device_info(self, data):
        """Process device information from the device"""

        try:
            # Parse the device info data
            device_info = self.parse_device_info(data)
            
            update_vals = {
                'device_name_info': device_info.get('DeviceName', ''),
                'mac': device_info.get('MAC', ''),
                'transaction_count': int(device_info.get('TransactionCount', 0)),
                'max_att_log_count': int(device_info.get('MaxAttLogCount', 0)),
                'user_count': int(device_info.get('UserCount', 0)),
                'max_user_count': int(device_info.get('MaxUserCount', 0)),
                'max_user_photo_count': int(device_info.get('MaxUserPhotoCount', 0)),
                'platform': device_info.get('Platform', ''),
                'oem_vendor': device_info.get('OEMVendor', ''),
                'fw_version': device_info.get('FWVersion', ''),
                'push_version': device_info.get('PushVersion', ''),
                'ip_address': device_info.get('IPAddress', ''),
                'max_face_count': int(device_info.get('MaxFaceCount', 0)),
                'language': int(device_info.get('Language', 0)),
            }

            # ESSL-specific fields
            update_vals.update({
                'photo_fun_on': bool(int(device_info.get('PhotoFunOn', 0))),
                'finger_fun_on': bool(int(device_info.get('FingerFunOn', 0))),
                'fp_version': device_info.get('FPVersion', ''),
                'max_finger_count': int(device_info.get('MaxFingerCount', 0)),
                'face_fun_on': bool(int(device_info.get('FaceFunOn', 0))),
                'face_version': device_info.get('FaceVersion', ''),
                'face_count': int(device_info.get('FaceCount', 0)),
                'fv_fun_on': bool(int(device_info.get('FvFunOn', 0))),
                'fv_version': device_info.get('FvVersion', ''),
                'max_fv_count': int(device_info.get('MaxFvCount', 0)),
                'fv_count': int(device_info.get('FvCount', 0)),
                'pv_fun_on': bool(int(device_info.get('PvFunOn', 0))),
                'pv_version': device_info.get('PvVersion', ''),
                'max_pv_count': int(device_info.get('MaxPvCount', 0)),
                'pv_count': int(device_info.get('PvCount', 0)),
                'multi_bio_data_support': device_info.get('MultiBioDataSupport', ''),
                'multi_bio_photo_support': device_info.get('MultiBioPhotoSupport', ''),
                'visilight_fun': bool(int(device_info.get('VisilightFun', 0))) if device_info.get('VisilightFun') else False,
                'ir_temp_detection_fun_on': bool(int(device_info.get('IRTempDetectionFunOn', 0))) if device_info.get('IRTempDetectionFunOn') else False,
                'mask_detection_fun_on': bool(int(device_info.get('MaskDetectionFunOn', 0))) if device_info.get('MaskDetectionFunOn') else False,
                'user_pic_url_fun_on': bool(int(device_info.get('UserPicURLFunOn', 0))) if device_info.get('UserPicURLFunOn') else False,
                'visual_intercom_fun_on': bool(int(device_info.get('VisualIntercomFunOn', 0))) if device_info.get('VisualIntercomFunOn') else False,
                'video_tid': device_info.get('VideoTID', ''),
                'qr_code_decrypt_fun_list': device_info.get('QRCodeDecryptFunList', ''),
                'video_protocol': device_info.get('VideoProtocol', ''),
                'is_support_qrcode': bool(int(device_info.get('IsSupportQRcode', 0))) if device_info.get('IsSupportQRcode') else False,
                'qr_code_enable': bool(int(device_info.get('QRCodeEnable', 0))) if device_info.get('QRCodeEnable') else False,
                'subcontracting_upgrade_fun_on': bool(int(device_info.get('SubcontractingUpgradeFunOn', 0))) if device_info.get('SubcontractingUpgradeFunOn') else False,
            })

            # Device type logic - ensure we always set a valid device_type
            device_type = 'other'  # Default fallback
            reg_device_type = device_info.get('RegDeviceType', '')
            
            # Check if the RegDeviceType is one of our valid options
            if reg_device_type in ['zk', 'essl']:
                device_type = reg_device_type
            # Check for ESSL device using serial number format
            elif self.serial_number and (self.serial_number.startswith('BRM') or self.serial_number.startswith('ESSL')):
                device_type = 'essl'
            # Check OEM vendor for ESSL
            elif 'ESSL' in device_info.get('OEMVendor', '').upper():
                device_type = 'essl'
            # Check for ZKTeco vendor
            elif any(zk_keyword in device_info.get('OEMVendor', '').upper() for zk_keyword in ['ZK', 'ZKTECO']):
                device_type = 'zk'
                
            update_vals['device_type'] = device_type
            
            self.write(update_vals)

            
        except Exception as e:

            raise

    def parse_device_info(self, data):
        info_dict = {}
        lines = data.split('\n')
        for line in lines:
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                if key.startswith('~'):
                    key = key[1:]  # Remove the '~' character
                info_dict[key] = value.strip()
        return info_dict

    def get_response_value(self):
        """Generate response string for device handshake"""

        
        # Store last request params for debugging
        request_params = dict(request.httprequest.args)
        self.sudo().write({
            'last_request_params': str(request_params),
            'last_handshake': fields.Datetime.now()
        })
        
        # Update device info from request params
        self._update_device_info_from_request()
        
        # Build the transflag from individual boolean fields
        transflag_value = 0
        if self.realtime:
            transflag_value |= 1
        if self.trans_flag_transdata:
            transflag_value |= (1 << 1)
        if self.trans_flag_attlog:
            transflag_value |= (1 << 2)
        if self.trans_flag_oplog:
            transflag_value |= (1 << 3)
        if self.trans_flag_attphoto:
            transflag_value |= (1 << 4)
        if self.trans_flag_enrolluser:
            transflag_value |= (1 << 5)
        if self.trans_flag_chguser:
            transflag_value |= (1 << 6)
        if self.trans_flag_enrollfp:
            transflag_value |= (1 << 7)
        if self.trans_flag_chgfp:
            transflag_value |= (1 << 8)
        if self.trans_flag_userpic:
            transflag_value |= (1 << 9)

        # Build response string with all parameters
        stamp_values = [
            f"ATTLOGStamp={self.attlog_stamp}",
            f"OPERLOGStamp={self.operlog_stamp}",
            f"ATTPHOTOStamp={self.attphoto_stamp}",
            f"ErrorDelay={self.error_delay}",
            f"Delay={self.delay}",
            f"TransTimes={self.trans_times}",
            f"TransInterval={self.trans_interval}",
            f"TransFlag={transflag_value}",
            f"TimeZone={self.time_zone}",
            f"Realtime={1 if self.realtime else 0}",
            f"Encrypt={self.encrypt}"
        ]
        
        # Add table stamp if specified
        if self.table_name_stamp and self.table_name_stamp != 'None':
            stamp_values.append(f"TableNameStamp={self.table_name_stamp}")
        
        # If device has PushOptionsFlag, add ServerVer
        if self.push_options_flag:
            stamp_values.append(f"ServerVer={self.server_ver}")
        
        # Join all parameters with \r\n
        response = '\r\n'.join(stamp_values)

        return response
        
    def _update_device_info_from_request(self):
        """Update device info from request parameters"""
        import logging
        _logger = logging.getLogger(__name__)
        
        request_params = dict(request.httprequest.args)
        _logger.info(f"Device request parameters: {request_params}")
        
        updates = {}
        
        # Map request parameters to device fields
        if 'pushver' in request_params:
            updates['push_version'] = request_params.get('pushver')
            
        if 'language' in request_params:
            try:
                updates['language'] = int(request_params.get('language'))
            except (ValueError, TypeError):
                pass
                
        if 'DeviceType' in request_params:
            # Map device type to allowed values
            device_type = request_params.get('DeviceType')
            _logger.info(f"Received DeviceType: {device_type}")
            
            if device_type == 'att':
                # Map 'att' to 'zk' as it's likely a ZKTeco device
                updates['device_type'] = 'zk'
                _logger.info(f"Mapped 'att' device type to 'zk'")
            elif device_type in ['zk', 'essl', 'other']:
                updates['device_type'] = device_type
                _logger.info(f"Using device_type as-is: {device_type}")
            else:
                # Default to 'other' for unknown device types
                updates['device_type'] = 'other'
                _logger.info(f"Mapped unknown device type '{device_type}' to 'other'")
            
        if 'PushOptionsFlag' in request_params:
            try:
                updates['push_options_flag'] = int(request_params.get('PushOptionsFlag'))
            except (ValueError, TypeError):
                pass
        
        _logger.info(f"Device updates to be applied: {updates}")
                
        # Update the device
        if updates:
            try:
                # Debug: log what we're trying to write
                _logger.info(f"About to write updates: {updates}")
                self.sudo().write(updates)
                _logger.info(f"Successfully updated device {self.name} with new info")
            except Exception as e:
                _logger.error(f"Error updating device: {str(e)}")
                _logger.error(f"Failed updates dict: {updates}")
                # Always try to recover from device_type errors
                try:
                    # Remove the problematic field and try again
                    safe_updates = {k: v for k, v in updates.items() if k != 'device_type'}
                    safe_updates['device_type'] = 'zk'  # Use a safe default
                    _logger.info(f"Attempting recovery with safe updates: {safe_updates}")
                    self.sudo().write(safe_updates)
                    _logger.info(f"Successfully recovered by setting device_type to 'zk'")
                except Exception as e2:
                    _logger.error(f"Recovery attempt also failed: {str(e2)}")
                    # Final fallback - just update the handshake
                    try:
                        self.sudo().write({'last_handshake': fields.Datetime.now()})
                        _logger.info(f"Final fallback: updated handshake only")
                    except Exception as e3:
                        _logger.error(f"Even handshake update failed: {str(e3)}")


    def action_send_initial_connection(self):
        for device in self:
            response = device.get_response_value()
            self._send_response_to_device(device, response)

    def _send_response_to_device(self, device, response):
        # Implement the actual sending logic here if needed
        pass

    def action_reboot_device(self):
        for device in self:
            command = 'REBOOT'
            self._send_to_device(device, command)

    def action_fetch_device_info(self):
        import logging
        _logger = logging.getLogger(__name__)
        
        for device in self:
            _logger.info(f"Fetching device info for device {device.name} (SN: {device.serial_number})")
            
            # Check if there's already a pending INFO command
            existing_command = self.env['device.command'].search([
                ('device_id', '=', device.id),
                ('command', '=', 'INFO'),
                ('status', '=', 'sent')
            ], limit=1)
            
            if existing_command:
                _logger.info(f"Found existing INFO command (ID: {existing_command.id}) for device {device.name}")
                # Reset the command to ensure it's sent again
                existing_command.write({'status': 'sent'})
                _logger.info(f"Reset existing command status to 'sent'")
            else:
                # Create a new INFO command
                command = 'INFO'
                command_id = self._send_to_device(device, command)
                _logger.info(f"Created new INFO command with ID {command_id} for device {device.name}")
            
            # Log all pending commands for this device
            pending_commands = self.env['device.command'].search([
                ('device_id', '=', device.id),
                ('status', '=', 'sent')
            ])
            
            _logger.info(f"Device {device.name} has {len(pending_commands)} pending commands: {[cmd.command for cmd in pending_commands]}")
            
            # Force update last_handshake to ensure device connects soon
            device.write({'last_handshake': fields.Datetime.now() - timedelta(minutes=5)})
            _logger.info(f"Updated last_handshake time to encourage device to connect soon")

    def action_download_user_info(self):
        for device in self:
            command = 'DATA QUERY USERINFO'
            self._send_to_device(device, command)

    def action_download_attendance(self):
        for device in self:
            command = 'CHECK'
            self._send_to_device(device, command)

    def _send_to_device(self, device, command):
        import logging
        _logger = logging.getLogger(__name__)
        
        _logger.info(f"Sending command '{command}' to device {device.name} (SN: {device.serial_number})")
        command_log = self.env['device.command'].create_command(device, command)
        
        if command_log:
            _logger.info(f"Command log created with ID {command_log.id}, status: {command_log.status}")
            return command_log.id
        else:
            _logger.error(f"Failed to create command log for device {device.name}")
            return False

    def process_data_from_device(self, method, SN, data, table):
        """
        Process data received from device based on method and table.
        This method handles both ZKTeco and ESSL devices.
        """


        
        try:
            # Check if it's ESSL device
            if self.device_type == 'essl':
                if method == 'cdata' and table == 'BIODATA':
                    return self._process_essl_biometric_data(data)
                elif method == 'cdata' and table == 'ATTLOG':
                    return self._process_essl_attendance_data(data)
            
            # Handle ZKTeco and other devices with existing logic
            if table == 'ATTLOG':
                return self._process_attendance_log(data)
            elif table == 'OPERLOG':
                return self._process_operation_log(data)
            elif table == 'ATTPHOTO':
                return self._process_att_photo(data)
            elif table == 'BIODATA':
                if self.device_type == 'essl':
                    return self._process_essl_biometric_data(data)
                else:
                    return self._process_biometric_data(data)
            elif table == 'OPLOG':
                return self._process_operation_log(data)
            elif table == 'options' or table == 'OPTIONS':
                import logging
                _logger = logging.getLogger(__name__)
                _logger.info(f"Processing options table data from device {self.name} (SN: {self.serial_number})")
                return self._process_options_data(data)
            else:
                import logging
                _logger = logging.getLogger(__name__)
                _logger.warning(f"Unsupported table {table} from device {self.name} (SN: {self.serial_number})")
                return f"ERROR: Unsupported table {table}"
        except Exception as e:

            return "ERROR=1"

    def _process_essl_biometric_data(self, data):
        """
        Process biometric data from ESSL devices
        Format: BIODATA Pin=X No=Y Index=Z Valid=V Duress=D Type=T MajorVer=MV MinorVer=mv Format=F Tmp=template
        """
        try:

            
            # Parse the biometric data
            params = {}
            for param in data.split():
                if '=' in param:
                    key, value = param.split('=', 1)
                    params[key] = value

            pin = params.get('Pin')
            if not pin:

                return "ERROR=1"
            
            # Get the user
            user = self.env['device.user'].search([
                ('device_id', '=', self.id),
                ('pin', '=', pin)
            ], limit=1)

            if not user:

                self._create_user(pin, params.get('Name', f'User {pin}'))
                user = self.env['device.user'].search([
                    ('device_id', '=', self.id),
                    ('pin', '=', pin)
                ], limit=1)
                if not user:
                    return "ERROR=1"

            # Create or update biometric data
            bio_type = params.get('Type', '0')
            biometric_data = self.env['biometric.data'].search([
                ('device_id', '=', self.id),
                ('user_id', '=', user.id),
                ('bio_type', '=', bio_type)
            ], limit=1)

            template = params.get('Tmp', '')
            vals = {
                'device_id': self.id,
                'user_id': user.id,
                'bio_type': bio_type,
                'template': template,
                'template_size': len(template),
                'valid': params.get('Valid', '0') == '1',
            }

            if biometric_data:
                biometric_data.write(vals)

            else:
                self.env['biometric.data'].create(vals)


            return "OK"

        except Exception as e:

            return "ERROR=1"

    def _process_essl_attendance_data(self, data):
        """
        Process attendance data from ESSL devices
        Format: ATTLOG Pin=X DateTime=Y Status=Z
        """
        try:

            processed_count = 0
            
            # Check if this is key-value paired data or tab-separated data
            if '=' in data:
                # Key-value paired format
                lines = data.strip().split('\n')
                for line in lines:
                    if not line.strip():
                        continue
                        
                    # Parse the attendance data
                    params = {}
                    for param in line.split():
                        if '=' in param:
                            key, value = param.split('=', 1)
                            params[key] = value

                    pin = params.get('Pin')
                    timestamp = params.get('DateTime')
                    status = params.get('Status', '0')
                    
                    if not pin or not timestamp:

                        continue

                    # Create attendance record with proper device_id
                    self.env['attendance.record'].create({
                        'device_id': self.id,  # Ensure device_id is set
                        'pin': pin,
                        'timestamp': timestamp,
                        'status': status,
                        'verify': 1,  # Default value
                        'workcode': 0  # Default value
                    })
                    processed_count += 1
            else:
                # This is a tab-separated format, use the standard processor
                return self._process_attendance_log(data)


            return f"OK:{processed_count}"

        except Exception as e:

            return "ERROR=1"

    def _process_options_data(self, data):
        """
        Process options data from ESSL device or ZKTeco device
        """
        import logging
        _logger = logging.getLogger(__name__)
        
        _logger.info(f"Processing options data: {data[:500]}" + ("..." if len(data) > 500 else ""))
        
        try:
            # The device is sending device information in a comma-separated format
            # We'll parse it and pass it to process_device_info
            
            # First, convert comma-separated format to key=value format if needed
            if ',' in data and '=' not in data:
                # This is a pure comma-separated format
                formatted_data = ""
                parts = data.split(',')
                keys = ['DeviceName', 'MAC', 'TransactionCount', 'MaxAttLogCount', 'UserCount', 'MaxUserCount', 
                        'MaxUserPhotoCount', 'Platform', 'OEMVendor', 'FWVersion', 'PushVersion', 'IPAddress', 'Language']
                
                for i, part in enumerate(parts):
                    if i < len(keys):
                        formatted_data += f"{keys[i]}={part.strip()}\n"
                
                data = formatted_data
            
            # Now process the data directly - this will update the device info
            _logger.info(f"Calling process_device_info with options data")
            self.process_device_info(data)
            return "OK"
                
        except Exception as e:
            _logger.error(f"Error processing options data: {str(e)}")
            return "ERROR=1"

    def _process_attendance_log(self, data):
        """
        Process attendance logs from the device
        Handles both tab-separated (ESSL) and space-separated (ZK) formats
        """

        
        lines = data.strip().split('\n')
        processed_count = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            try:
                # Detect if the line is tab-separated (ESSL) or space-separated (ZK)
                if '\t' in line:
                    # ESSL format is tab-separated
                    parts = line.split('\t')
                    # ESSL format: PIN TAB Timestamp TAB Status TAB Verify TAB Workcode
                    if len(parts) >= 5:
                        pin = parts[0]
                        timestamp_str = parts[1]
                        status = int(parts[2])
                        verify = int(parts[3])
                        workcode = int(parts[4]) if parts[4].strip() else 0
                        reserved_1 = int(parts[6]) if len(parts) > 6 and parts[6].strip() else 0
                        reserved_2 = int(parts[8]) if len(parts) > 8 and parts[8].strip() else 0
                    else:

                        continue
                else:
                    # ZK format is space-separated
                    parts = line.strip().split()
                    if len(parts) >= 7:
                        pin = parts[0]
                        timestamp_str = f"{parts[1]} {parts[2]}"
                        status = int(parts[3])
                        verify = int(parts[4])
                        workcode = int(parts[5])
                        reserved_1 = int(parts[6])
                        reserved_2 = int(parts[9]) if len(parts) >= 10 else int(parts[6])
                    else:

                        continue
                
                # Convert timestamp to UTC
                device_tz = pytz.timezone(self.device_time_zone) if self.device_time_zone else pytz.utc
                try:
                    timestamp_naive = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    timestamp_device = device_tz.localize(timestamp_naive)
                    timestamp_utc = timestamp_device.astimezone(pytz.utc)
                    timestamp_naive_utc = timestamp_utc.replace(tzinfo=None)
                except ValueError as e:

                    continue

                # Check for existing record to avoid duplicates
                existing_record = self.env['attendance.record'].search([
                    ('device_id', '=', self.id),
                    ('pin', '=', pin),
                    ('timestamp', '=', timestamp_naive_utc)
                ], limit=1)

                if not existing_record:
                    # Create attendance record with all fields
                    record_data = {
                        'device_id': self.id,  # Ensure device_id is set
                        'pin': pin,
                        'timestamp': timestamp_naive_utc,
                        'status': status,
                        'verify': verify,
                        'workcode': workcode,
                        'reserved_1': reserved_1,
                        'reserved_2': reserved_2
                    }
                    
                    self.env['attendance.record'].create(record_data)
                    processed_count += 1
                    
            except Exception as e:

                continue
                
        return f"OK:{processed_count}"

    def _process_operation_log(self, data):
        try:
            # Use a transaction savepoint to handle potential conflicts
            with self.env.cr.savepoint():
                # First try to find by content hash to avoid creating duplicate records
                # Calculate hash here for consistency
                content_hash = hashlib.sha256(data.encode()).hexdigest()
                
                # Check if this exact log content already exists for this device
                existing_log = self.env['operation.log'].search([
                    ('device_id', '=', self.id),
                    ('content_hash', '=', content_hash)
                ], limit=1)
                
                if existing_log:
                    # If the log exists but hasn't been processed, process it
                    if not existing_log.processed:
                        existing_log.process_log_content()
                    return 'OK'
                else:
                    try:
                        # Create the log with pre-calculated hash to avoid compute timing issues
                        operation_log = self.env['operation.log'].create({
                            'device_id': self.id,
                            'log_content': data,
                            'content_hash': content_hash,
                        })
                        operation_log.process_log_content()
                        return 'OK'
                    except Exception as e:
                        # Exception handling for potential unique constraint errors

                        
                        # Attempt to find and process a potential duplicate that was just created
                        # by another concurrent transaction
                        duplicate_log = self.env['operation.log'].search([
                            ('device_id', '=', self.id),
                            ('content_hash', '=', content_hash)
                        ], limit=1)
                        
                        if duplicate_log and not duplicate_log.processed:
                            duplicate_log.process_log_content()
                        
                        return 'OK'
        except Exception as e:

            # Return OK to the device even if there's an error to prevent retries
            return 'OK'

    def _compute_operation_log_count(self):
        for device in self:
            device.operation_log_count = self.env['operation.log'].search_count([
                ('device_id', '=', device.id)
            ])
            
    @api.model
    def auto_configure_device(self, serial_number):
        """
        Auto-configure a device that was automatically created from a push request
        This is done immediately when the device connects, not via cron job
        """
        try:
            device = self.search([('serial_number', '=', serial_number)], limit=1)
            if not device:
                return False
                
            # Set the device state to active if it's in draft
            if device.device_state == 'draft':
                device.write({
                    'device_state': 'active',
                    'last_handshake': fields.Datetime.now()
                })
                
            # Immediately send commands to fetch device info
            device.action_fetch_device_info()
            
            # Also fetch user information
            device.action_download_user_info()
            
            # And download attendance data
            device.action_download_attendance()
            
            return device
        except Exception as e:
            # Log the exception for debugging
            import traceback
            traceback.print_exc()
            return False

    def action_view_operation_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Operation Logs',
            'res_model': 'operation.log',
            'view_mode': 'tree,form',
            'domain': [('device_id', '=', self.id)],
            'context': {'default_device_id': self.id}
        }

    @api.model
    def _update_device_status(self):
        """
        Cron job to update device status
        This ensures the kanban view colors are updated even when the page is not refreshed
        """
        devices = self.search([])
        devices._compute_device_status()
        return True
        
    # Methods removed as we're handling device creation and configuration immediately at HTTP handshake

    # Device state change methods
    def action_set_to_draft(self):
        self.ensure_one()
        self.device_state = 'draft'
        return True
        
    def action_activate(self):
        self.ensure_one()
        self.device_state = 'active'
        return True
        
    def action_deactivate(self):
        self.ensure_one()
        self.device_state = 'inactive'
        return True

    def action_archive_device(self):
        """Archive the device by setting active to False"""
        self.ensure_one()
        self.write({
            'active': False
        })
        # Return a window action to reload the view
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _process_biometric_data(self, data):
        """
        Process biometric data from ESSL device
        Handles both tab-separated and space-separated (or mixed) BIODATA lines.
        Format: BIODATA Pin=X No=Y Index=Z Valid=V Duress=D Type=T MajorVer=MV MinorVer=mv Format=F Tmp=template
        """

        
        for line in data.split('\n'):
            if not line.strip():
                continue
            try:
                # Try splitting on any whitespace (tab, space, or mixed)
                parts = [part for part in re.split(r'[ \t]+', line.strip()) if '=' in part]
                if not parts or len(parts) < 2:
                    # Fallback: try splitting by space only (legacy)
                    parts = [part for part in line.strip().split(' ') if '=' in part]
                kv = dict(part.split('=', 1) for part in parts)
                
                # Extract required fields
                pin = kv.get('Pin')
                template = kv.get('Tmp')
                template_size = len(template) if template else 0
                valid = kv.get('Valid', '0') == '1'
                bio_type = kv.get('Type', 'FP')  # Default to fingerprint if not specified
                
                if not pin or not template:

                    continue
                
                # Find the device user
                device_user = self.env['device.user'].search([
                    ('device_id', '=', self.id),
                    ('pin', '=', pin)
                ], limit=1)
                
                if not device_user:

                    continue
                
                # Create or update biometric data record
                bio_data = self.env['biometric.data'].search([
                    ('device_id', '=', self.id),
                    ('user_id', '=', device_user.id),
                    ('bio_type', '=', bio_type)
                ], limit=1)
                
                if bio_data:
                    bio_data.write({
                        'template': template,
                        'template_size': template_size,
                        'valid': valid
                    })
                else:
                    self.env['biometric.data'].create({
                        'device_id': self.id,
                        'user_id': device_user.id,
                        'bio_type': bio_type,
                        'template': template,
                        'template_size': template_size,
                        'valid': valid
                    })
                

                
            except Exception as e:

                continue
        return 'OK'