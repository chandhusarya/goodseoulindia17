def pre_init_hook(env):
    """
    Pre-init hook to optimize table creation and indexing during installation.
    """
    # Get the cursor from the environment
    cr = env.cr
    
    # Create tables with optimized settings
    tables_to_create = [
        ('attendance_record', """
            CREATE TABLE IF NOT EXISTS attendance_record (
                id serial PRIMARY KEY,
                create_uid integer,
                create_date timestamp without time zone,
                write_uid integer,
                write_date timestamp without time zone,
                device_id integer NOT NULL,
                pin varchar NOT NULL,
                timestamp timestamp without time zone NOT NULL,
                status integer NOT NULL,
                verify integer NOT NULL,
                workcode integer,
                reserved_1 integer,
                reserved_2 integer,
                attendance_process_id integer,
                is_duplicate boolean DEFAULT false
            ) WITH (fillfactor = 90)
        """),
        ('device_user', """
            CREATE TABLE IF NOT EXISTS device_user (
                id serial PRIMARY KEY,
                create_uid integer,
                create_date timestamp without time zone,
                write_uid integer,
                write_date timestamp without time zone,
                device_id integer NOT NULL,
                pin varchar NOT NULL,
                name varchar,
                employee_id integer,
                privilege integer,
                password varchar,
                card varchar,
                "group" varchar,
                time_zone varchar
            ) WITH (fillfactor = 90)
        """),
        ('fingerprint_template', """
            CREATE TABLE IF NOT EXISTS fingerprint_template (
                id serial PRIMARY KEY,
                create_uid integer,
                create_date timestamp without time zone,
                write_uid integer,
                write_date timestamp without time zone,
                device_id integer NOT NULL,
                user_id integer NOT NULL,
                fid integer,
                size integer,
                valid boolean,
                template text
            )
        """),
        ('operation_log', """
            CREATE TABLE IF NOT EXISTS operation_log (
                id serial PRIMARY KEY,
                create_uid integer,
                create_date timestamp without time zone,
                write_uid integer,
                write_date timestamp without time zone,
                device_id integer NOT NULL,
                log_content text NOT NULL,
                processed boolean DEFAULT false,
                processing_result text,
                content_hash varchar
            )
        """)
    ]
    
    # Create tables with optimized settings
    for table_name, create_sql in tables_to_create:
        cr.execute(create_sql)
    
    # Create indexes for each table
    for table_name, _ in tables_to_create:
        # Create standard indexes
        cr.execute(f"""
            CREATE INDEX IF NOT EXISTS 
            {table_name}_create_date_idx ON {table_name} (create_date)
        """)
        
        cr.execute(f"""
            CREATE INDEX IF NOT EXISTS 
            {table_name}_write_date_idx ON {table_name} (write_date)
        """)
    
    # Create specific indexes for attendance_record
    cr.execute("""
        CREATE INDEX IF NOT EXISTS 
        attendance_record_device_pin_idx ON attendance_record (device_id, pin)
    """)
    
    cr.execute("""
        CREATE INDEX IF NOT EXISTS 
        attendance_record_timestamp_idx ON attendance_record (timestamp)
    """)

def post_init_hook(cr_or_env, registry=None):
    """
    Post-init hook to handle duplicate user_picture records and create constraints.
    """
    from odoo import api, SUPERUSER_ID
    import logging
    
    _logger = logging.getLogger(__name__)
    
    # Handle both types of parameters (cr or env)
    if hasattr(cr_or_env, 'cr'):
        # If env is passed
        env = cr_or_env
        cr = env.cr
    else:
        # If cr is passed (traditional way)
        cr = cr_or_env
        env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Handle duplicate records
    if 'user.picture' in env:
        try:
            env['user.picture']._handle_duplicate_records()
        except Exception as e:
            _logger.warning(f"Error handling duplicate user.picture records: {e}")
    
    # Create constraints after data is loaded - using DO block for safer execution
    try:
        cr.execute("""
            DO $$
            BEGIN
                -- Add constraints for attendance_record if it doesn't already exist
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'unique_attendance_device_pin_timestamp'
                ) THEN
                    ALTER TABLE attendance_record 
                    ADD CONSTRAINT unique_attendance_device_pin_timestamp 
                    UNIQUE (device_id, pin, timestamp);
                END IF;
                
                -- Add constraints for device_user if it doesn't already exist
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'unique_device_pin'
                ) THEN
                    ALTER TABLE device_user 
                    ADD CONSTRAINT unique_device_pin 
                    UNIQUE (device_id, pin);
                END IF;
                
                -- Add constraints for fingerprint_template if it doesn't already exist
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'unique_device_user_fid'
                ) THEN
                    ALTER TABLE fingerprint_template 
                    ADD CONSTRAINT unique_device_user_fid 
                    UNIQUE (device_id, user_id, fid);
                END IF;
                
                -- Add constraints for operation_log if it doesn't already exist
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'unique_device_content_hash'
                ) THEN
                    ALTER TABLE operation_log 
                    ADD CONSTRAINT unique_device_content_hash 
                    UNIQUE (device_id, content_hash);
                END IF;
            END $$;
        """)
    except Exception as e:
        _logger.warning(f"Error creating constraints: {e}")
        # Continue installation even if constraints fail

def pre_uninstall_hook(cr_or_env, registry=None):
    """Pre-uninstall hook to properly remove constraints and handle data deletion"""
    import logging
    _logger = logging.getLogger(__name__)
    
    # Handle both types of parameters (cr or env)
    if hasattr(cr_or_env, 'cr'):
        # If env is passed
        cr = cr_or_env.cr
    else:
        # If cr is passed (traditional way)
        cr = cr_or_env
        
    try:
        # Drop constraints that might cause lock timeouts
        cr.execute("""
            DO $$
            BEGIN
                -- Drop hr_employee constraints
                IF EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'hr_employee_fingerprint_no_unique'
                ) THEN
                    ALTER TABLE hr_employee DROP CONSTRAINT IF EXISTS hr_employee_fingerprint_no_unique;
                END IF;

                -- Drop attendance record constraints
                IF EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'unique_attendance_device_pin_timestamp'
                ) THEN
                    ALTER TABLE attendance_record DROP CONSTRAINT IF EXISTS unique_attendance_device_pin_timestamp;
                END IF;

                -- Drop device user constraints
                IF EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'unique_device_pin'
                ) THEN
                    ALTER TABLE device_user DROP CONSTRAINT IF EXISTS unique_device_pin;
                END IF;

                -- Drop fingerprint template constraints
                IF EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'unique_device_user_fid'
                ) THEN
                    ALTER TABLE fingerprint_template DROP CONSTRAINT IF EXISTS unique_device_user_fid;
                END IF;

                -- Drop operation log constraints
                IF EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'unique_device_content_hash'
                ) THEN
                    ALTER TABLE operation_log DROP CONSTRAINT IF EXISTS unique_device_content_hash;
                END IF;
            END $$;
        """)
    except Exception as e:
        _logger.warning(f"Error dropping constraints: {e}")
    
    # Define tables to clean up
    tables = [
        'attendance_record',
        'device_user',
        'fingerprint_template',
        'operation_log',
        'attendance_process',
        'attendance_config_settings'
    ]
    
    # Clear data in batches to prevent memory issues
    for table in tables:
        try:
            # First check if table exists before attempting to delete from it
            cr.execute(f"""
                SELECT EXISTS (
                   SELECT FROM information_schema.tables 
                   WHERE table_name = '{table}'
                );
            """)
            table_exists = cr.fetchone()[0]
            
            if table_exists:
                cr.execute(f"""
                    DO $$
                    DECLARE
                        batch_size INTEGER := 1000;
                        deleted INTEGER;
                    BEGIN
                        LOOP
                            WITH rows AS (
                                SELECT id FROM {table}
                                LIMIT batch_size
                                FOR UPDATE SKIP LOCKED
                            )
                            DELETE FROM {table} t
                            USING rows
                            WHERE t.id = rows.id;
                            
                            GET DIAGNOSTICS deleted = ROW_COUNT;
                            EXIT WHEN deleted = 0;
                            COMMIT;
                        END LOOP;
                    END $$;
                """)
        except Exception as e:
            _logger.warning(f"Error cleaning up table {table}: {e}")
            continue
