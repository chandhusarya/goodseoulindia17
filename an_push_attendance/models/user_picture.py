# models/user_picture.py
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import base64

class UserPicture(models.Model):
    _name = 'user.picture'
    _description = 'User Picture'
    _rec_name = 'file_name'

    device_id = fields.Many2one('attendance.device', string='Device', required=True)
    user_id = fields.Many2one('device.user', string='User', required=True, ondelete='cascade')
    file_name = fields.Char(string='File Name', required=True)
    size = fields.Integer(string='Size')
    content = fields.Text(string='Raw Content')
    image = fields.Binary(string='Image', compute='_compute_image', store=True)
    image_medium = fields.Binary(string='Medium Image', compute='_compute_image', store=True)
    image_small = fields.Binary(string='Small Image', compute='_compute_image', store=True)
    active = fields.Boolean(default=True, string='Active')

    @api.constrains('device_id', 'user_id', 'file_name', 'active')
    def _check_unique_active_picture(self):
        """
        API constraint to ensure uniqueness of active pictures.
        This allows more flexibility than SQL constraint.
        """
        for record in self:
            if record.active:
                # Check for other active records with same device, user, and filename
                domain = [
                    ('device_id', '=', record.device_id.id),
                    ('user_id', '=', record.user_id.id),
                    ('file_name', '=', record.file_name),
                    ('active', '=', True),
                    ('id', '!=', record.id)  # Exclude current record
                ]
                duplicate_count = self.search_count(domain)
                
                if duplicate_count > 0:
                    # Instead of raising error, archive the duplicates
                    duplicates = self.search(domain)
                    if duplicates:
                        duplicates.write({'active': False})
    
    @api.depends('content')
    def _compute_image(self):
        for record in self:
            try:
                if record.content:
                    try:
                        # First try: assume content is already base64
                        image_data = base64.b64decode(record.content)
                        record.image = record.content
                        record.image_medium = record.content  # Using same image for medium
                        record.image_small = record.content   # Using same image for small
                    except:
                        try:
                            # Second try: encode the content to base64
                            image_data = base64.b64encode(record.content.encode())
                            record.image = image_data
                            record.image_medium = image_data  # Using same image for medium
                            record.image_small = image_data   # Using same image for small
                        except:
                            record.image = False
                            record.image_medium = False
                            record.image_small = False
                else:
                    record.image = False
                    record.image_medium = False
                    record.image_small = False
            except Exception:
                record.image = False
                record.image_medium = False
                record.image_small = False

    def unlink(self):
        """Override unlink to archive instead of delete"""
        for record in self:
            record.write({'active': False})
        return True

    @api.model
    def _handle_duplicate_records(self):
        """
        Handle duplicate user_picture records.
        This method will keep the most recent record for each unique combination of device_id, user_id, and file_name,
        and archive the older duplicates.
        """
        self.env.cr.execute("""
            SELECT device_id, user_id, file_name, array_agg(id ORDER BY id DESC) as ids
            FROM user_picture
            WHERE active = TRUE
            GROUP BY device_id, user_id, file_name
            HAVING COUNT(*) > 1
        """)
        
        duplicates = self.env.cr.fetchall()
        
        for device_id, user_id, file_name, ids in duplicates:
            # Keep the first ID (most recent) and archive the rest
            keep_id = ids[0]
            archive_ids = ids[1:]
            
            if archive_ids:
                self.browse(archive_ids).write({'active': False})
                
        return True