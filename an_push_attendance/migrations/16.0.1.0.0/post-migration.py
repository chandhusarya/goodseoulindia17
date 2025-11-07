from odoo import api, SUPERUSER_ID

def migrate(cr, version):
    """
    Verify that the unique constraint was properly applied and log the results.
    """
    # Check if there are any remaining duplicates (should be none after pre-migration)
    cr.execute("""
        SELECT COUNT(*) 
        FROM (
            SELECT device_id, user_id, file_name
            FROM user_picture
            WHERE active = TRUE
            GROUP BY device_id, user_id, file_name
            HAVING COUNT(*) > 1
        ) as duplicates
    """)
    
    remaining_duplicates = cr.fetchone()[0]
    
    if remaining_duplicates > 0:
        print(f"WARNING: There are still {remaining_duplicates} sets of duplicate active records in user_picture table")
    else:
        print("Post-migration: No duplicate active records found in user_picture table. Constraint should be applied successfully.") 