from odoo import models, fields, api
from datetime import datetime, timedelta
import hashlib
import logging

_logger = logging.getLogger(__name__)

class OperationLog(models.Model):
    _name = 'operation.log'
    _description = 'Operation Log'
    _order = 'create_date DESC'  # Most recent logs first for better performance

    device_id = fields.Many2one('attendance.device', string='Device', required=True, index=True)
    log_content = fields.Text(string='Log Content', required=True)
    log_content_large = fields.Binary(string='Large Content', attachment=True)
    processed = fields.Boolean(string='Processed', default=False, index=True)
    processing_result = fields.Text(string='Processing Result')

    content_hash = fields.Char(string='Content Hash', index=True)
    
    _sql_constraints = [
        ('unique_device_content_hash',
         'UNIQUE(device_id, content_hash)',
         'This log content already exists for this device!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        # Process each vals dict to compute content_hash if needed
        for vals in vals_list:
            if 'content_hash' not in vals and 'log_content' in vals:
                content = vals.get('log_content_large', False)
                if content:
                    content = content.decode() 
                else:
                    content = vals.get('log_content', '')
                vals['content_hash'] = hashlib.sha256(content.encode()).hexdigest()
        
        # Use savepoint to handle race conditions on create
        with self.env.cr.savepoint():
            try:
                return super().create(vals_list)
            except Exception as e:
                # If creation fails due to unique constraint, 
                # find and return the existing records
                if 'unique_device_content_hash' in str(e):
                    _logger.info(f"Duplicate operation log detected, finding existing records")
                    existing_records = []
                    for vals in vals_list:
                        if 'content_hash' in vals:
                            existing = self.search([
                                ('device_id', '=', vals.get('device_id')),
                                ('content_hash', '=', vals.get('content_hash')),
                            ], limit=1)
                            if existing:
                                existing_records.append(existing)
                    if existing_records:
                        return existing_records
                # Re-raise if not a duplicate or if duplicate not found
                raise

    def process_log_content(self):
        for log in self:
            try:
                # Use a savepoint to prevent processing failures from affecting other logs
                with self.env.cr.savepoint():
                    # Get the full content
                    content = log.log_content_large.decode() if log.log_content_large else log.log_content
                    if not content:
                        continue

                    lines = content.strip().split('\n')
                    for line in lines:
                        if line.startswith('USER PIN'):
                            self._process_user_info(log.device_id, line)
                        elif line.startswith('FP PIN'):
                            self._process_fingerprint_template(log.device_id, line)
                        elif line.startswith('USERPIC PIN'):
                            self._process_user_picture(log.device_id, line)
                        elif line.startswith('FACE PIN'):
                            self._process_face_template(log.device_id, line)

                    log.write({
                        'processed': True,
                        'processing_result': 'Successfully processed'
                    })
            except Exception as e:
                import traceback
                _logger.error(f"Error processing log {log.id}: {str(e)}\n{traceback.format_exc()}")
                log.write({
                    'processed': True,
                    'processing_result': f'Error processing: {str(e)}'
                })

    def _process_user_info(self, device, user_info):
        user_data = {}
        parts = user_info.split()
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                user_data[key.strip()] = value.strip()

        pin = user_data.get('PIN')
        if not pin:
            return

        existing_user = self.env['device.user'].search([
            ('device_id', '=', device.id),
            ('pin', '=', pin)
        ], limit=1)

        if existing_user:
            existing_user.write({
                'name': user_data.get('Name'),
                'privilege': int(user_data.get('Pri', 0)),
                'password': user_data.get('Passwd'),
                'card': user_data.get('Card'),
                'group': user_data.get('Grp'),
                'time_zone': user_data.get('TZ'),
                'verify': int(user_data.get('Verify', 0)),
                'vice_card': user_data.get('ViceCard'),
                'post_data': user_info,
            })
        else:
            self.env['device.user'].create({
                'device_id': device.id,
                'pin': pin,
                'name': user_data.get('Name'),
                'privilege': int(user_data.get('Pri', 0)),
                'password': user_data.get('Passwd'),
                'card': user_data.get('Card'),
                'group': user_data.get('Grp'),
                'time_zone': user_data.get('TZ'),
                'verify': int(user_data.get('Verify', 0)),
                'vice_card': user_data.get('ViceCard'),
                'post_data': user_info,
            })

    def _process_fingerprint_template(self, device, fp_info):
        fp_data = {}
        parts = fp_info.split()
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                fp_data[key.strip()] = value.strip()

        pin = fp_data.get('PIN')
        fid = int(fp_data.get('FID', 0))
        size = int(fp_data.get('Size', 0))
        valid = fp_data.get('Valid') == '1'
        template = fp_data.get('TMP')

        if not pin or not fid:
            return

        user = self.env['device.user'].search([('device_id', '=', device.id), ('pin', '=', pin)], limit=1)
        if user:
            existing_fp = self.env['fingerprint.template'].search([
                ('device_id', '=', device.id),
                ('user_id', '=', user.id),
                ('fid', '=', fid)
            ], limit=1)

            if existing_fp:
                existing_fp.write({
                    'size': size,
                    'valid': valid,
                    'template': template,
                })
            else:
                self.env['fingerprint.template'].create({
                    'device_id': device.id,
                    'user_id': user.id,
                    'fid': fid,
                    'size': size,
                    'valid': valid,
                    'template': template,
                })

    def _process_user_picture(self, device, pic_info):
        """Enhanced user picture processing to handle re-downloading"""
        pic_data = {}
        parts = pic_info.split()
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                pic_data[key.strip()] = value.strip()

        pin = pic_data.get('PIN')
        file_name = pic_data.get('FileName')
        size = int(pic_data.get('Size', 0))
        content = pic_data.get('Content')

        if not pin or not file_name:
            return

        user = self.env['device.user'].search([
            ('device_id', '=', device.id),
            ('pin', '=', pin)
        ], limit=1)

        if not user:
            return

        # Search for existing picture including inactive ones
        existing_picture = self.env['user.picture'].with_context(active_test=False).search([
            ('device_id', '=', device.id),
            ('user_id', '=', user.id),
            ('file_name', '=', file_name)
        ], limit=1)

        picture_vals = {
            'device_id': device.id,
            'user_id': user.id,
            'file_name': file_name,
            'size': size,
            'content': content,
            'active': True,
        }

        if existing_picture:
            # If picture exists but is inactive, reactivate it with new content
            existing_picture.write(picture_vals)
        else:
            # Create new picture
            self.env['user.picture'].create(picture_vals)

    def _process_face_template(self, device, face_info):
        """Enhanced face template processing to handle multiple FIDs"""
        face_data = {}
        parts = face_info.split()
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                face_data[key.strip()] = value.strip()

        pin = face_data.get('PIN')
        fid = int(face_data.get('FID', 0))
        size = int(face_data.get('SIZE', 0))
        valid = face_data.get('VALID') == '1'
        template = face_data.get('TMP')

        if not pin or fid < 0:
            return

        user = self.env['device.user'].search([
            ('device_id', '=', device.id),
            ('pin', '=', pin)
        ], limit=1)

        if not user:
            return

        # Check for existing template
        existing_face = self.env['face.template'].search([
            ('device_id', '=', device.id),
            ('user_id', '=', user.id),
            ('fid', '=', fid),
            ('active', '=', True)
        ], limit=1)

        template_vals = {
            'size': size,
            'valid': valid,
            'template': template,
            'state': 'active'
        }

        if existing_face:
            # Only update if template content changed
            if existing_face.template != template:
                existing_face.write(template_vals)
        else:
            # Create new template
            self.env['face.template'].create({
                'device_id': device.id,
                'user_id': user.id,
                'fid': fid,
                **template_vals
            })

    def auto_cleanup_logs(self):
        """
        Automated cleanup for old operation logs to prevent database bloat
        Keeps recent 14 days of logs by default
        """
        # Keep logs for the past 14 days, delete older ones
        cutoff_date = fields.Datetime.now() - timedelta(days=14)
        
        # Use SQL for better performance on large datasets
        self.env.cr.execute("""
            DELETE FROM operation_log
            WHERE create_date < %s
            AND processed = true
            LIMIT 5000
        """, (cutoff_date,))
        
        return True

    @api.model
    def batch_process_pending_logs(self, batch_size=100):
        """
        Process pending operation logs in batches to avoid memory issues
        """
        pending_logs = self.search([
            ('processed', '=', False)
        ], limit=batch_size, order='create_date')
        
        if pending_logs:
            _logger.info(f"Processing batch of {len(pending_logs)} pending operation logs")
            pending_logs.process_log_content()
        
        return bool(pending_logs)

    @api.model
    def _cron_process_pending_logs(self):
        """
        Cron job to process pending logs
        Process in batches until no more pending logs are found
        """
        batch_size = 100
        max_batches = 50  # Process up to 5000 logs per cron run
        
        for i in range(max_batches):
            if not self.batch_process_pending_logs(batch_size):
                break
                
        return True

    @api.model
    def cleanup_duplicate_logs(self):
        """
        Clean up duplicate logs that might have been created during high traffic
        """
        # Find duplicate logs based on content hash
        self.env.cr.execute("""
            SELECT l1.id
            FROM operation_log l1
            JOIN (
                SELECT device_id, content_hash, MIN(id) as min_id
                FROM operation_log
                GROUP BY device_id, content_hash
                HAVING COUNT(*) > 1
            ) l2 ON l1.device_id = l2.device_id 
                AND l1.content_hash = l2.content_hash 
                AND l1.id != l2.min_id
            LIMIT 500
        """)
        
        duplicate_ids = [r[0] for r in self.env.cr.fetchall()]
        if duplicate_ids:
            _logger.info(f"Cleaning up {len(duplicate_ids)} duplicate operation logs")
            self.browse(duplicate_ids).unlink()
            
        return bool(duplicate_ids)