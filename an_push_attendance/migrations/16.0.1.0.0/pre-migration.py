from odoo import api, SUPERUSER_ID

def migrate(cr, version):
    """
    Remove the old SQL constraint before applying the new API constraint.
    """
    # Try to drop the old constraint if it exists
    cr.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'user_picture_unique_device_user_file'
            ) THEN
                ALTER TABLE user_picture DROP CONSTRAINT IF EXISTS user_picture_unique_device_user_file;
            END IF;
        END $$;
    """)
    
    print("Pre-migration: Removed old SQL constraint 'user_picture_unique_device_user_file' if it existed") 