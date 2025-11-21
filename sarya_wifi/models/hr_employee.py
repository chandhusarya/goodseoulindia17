from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError, ValidationError, AccessError
import random
import re
import psycopg2

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    wifi_login = fields.Char(string="WiFi Login")
    wifi_password = fields.Char(string="WiFi Password")


    def get_radius_connection(self):

        host = self.env['ir.config_parameter'].sudo().get_param('radius.host', False)
        user = self.env['ir.config_parameter'].sudo().get_param('radius.user', False)
        password = self.env['ir.config_parameter'].sudo().get_param('radius.password', False)

        port = 5432
        dbname = "radius"

        if not host:
            raise UserError(_("Radius host is not configured (radius.host). Please contact system administrator"))

        if not user:
            raise UserError(_("Radius user is not configured (radius.user). Please contact system administrator"))

        if not password:
            raise UserError(_("Radius password is not configured (radius.password). Please contact system administrator"))



        return (host,port,dbname,user,password)




    def toggle_active(self):
        res = super(HrEmployee, self).toggle_active()

        archived_employees = self.filtered(lambda e: not e.active)
        archived_employees.action_revoke_wifi_credentials()

        return res


    def action_revoke_wifi_credentials(self):
        print("revoke")

        for employee in self:

            password_history_records = self.env['wifi.password.history'].search([('employee_id', '=', employee.id), ('is_removed_from_server', '=', False)])

            employee.wifi_login = False
            employee.wifi_password = False

            for record in password_history_records:

                record.is_removed_from_server = True
                radius_host,radius_port,radius_dbname,radius_user,radius_password = self.get_radius_connection()

                username = record.wifi_login

                try:
                    conn = psycopg2.connect(
                        host=radius_host,
                        port=radius_port,
                        dbname=radius_dbname,
                        user=radius_user,
                        password=radius_password,
                        sslmode="require"
                    )
                    cur = conn.cursor()

                    # Delete from radcheck
                    cur.execute("DELETE FROM radcheck WHERE username = %s", (username,))

                    # Optional cleanup if user has entries in other tables
                    cur.execute("DELETE FROM radreply WHERE username = %s", (username,))
                    cur.execute("DELETE FROM radusergroup WHERE username = %s", (username,))

                    conn.commit()
                    cur.close()
                    conn.close()

                except Exception as e:
                    raise UserError(_("Error %s" % str(e)))







    def action_generate_wifi_credentials(self):

        print("ddddddddddddddddddddddd")

        for employee in self:

            employee.action_revoke_wifi_credentials()

            username, password = self.generate_wifi_credentials(employee.name)
            employee.wifi_login = username
            employee.wifi_password = password


            self.env['wifi.password.history'].create({
                'employee_id': employee.id,
                'wifi_login': username,
                'wifi_password': password,
            })

            radius_host,radius_port,radius_dbname,radius_user,radius_password = self.get_radius_connection()

            try:
                conn = psycopg2.connect(
                    host=radius_host,
                    port=radius_port,
                    dbname=radius_dbname,
                    user=radius_user,
                    password=radius_password,
                    sslmode="require"
                )
                cur = conn.cursor()

                # --- the actual insert ---
                sql = """
                        INSERT INTO radcheck (username, attribute, op, value)
                        VALUES (%s, 'Cleartext-Password', ':=', %s)
                    """
                cur.execute(sql, (username, password))
                conn.commit()

                print(f"✅ User '{username}' created successfully.")

                cur.close()
                conn.close()

            except Exception as e:
                raise UserError(_("Error %s" % str(e)))







    def generate_wifi_credentials(self, employee_name):

        #Check username uniqueness
        username = self.generate_wifi_username(employee_name)

        # Password pattern example
        word_roots = ["sun", "sky", "pro", "win", "max", "top", "joy", \
                      "ace", "vip", "gal", "zen", "star", "neo", "fly",\
                      "leo", "fun", "red", "big", "new"]
        root = random.choice(word_roots)  # 3 letters meaningful root
        chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
        random_part = "".join(random.choice(chars) for _ in range(4))
        password = root + random_part  # total 7 chars

        return username, password


    def generate_wifi_username(self, employee_name):

        # Clean extra spaces
        name = employee_name.strip()

        # Split into parts
        parts = re.split(r"\s+", name)

        if len(parts) < 2:
            raise ValueError("Full name required (first and last name)")

        prefix = self.env['ir.config_parameter'].sudo().get_param('radius.prefix', False)
        if not prefix:
            raise UserError(_("Radius username prefix is not configured (radius.prefix). Please contact system administrator"))

        first = parts[0].lower()
        last = parts[-1].lower()

        # Username
        username = f"{prefix}.{first}.{last}"

        # Ensure uniqueness
        is_username_unique = self.is_wifi_username_unique(username)
        if not is_username_unique:
            suffix = 1
            while True:
                new_username = f"{username}{suffix}"
                if self.is_wifi_username_unique(new_username):
                    username = new_username
                    break
                suffix += 1

        return username

    def is_wifi_username_unique(self, username):
        """
        Returns True if username does NOT exist in radcheck table.
        Returns False if username already exists.
        """
        radius_host,radius_port,radius_dbname,radius_user,radius_password = self.get_radius_connection()

        try:
            conn = psycopg2.connect(
                host=radius_host,
                port=radius_port,
                dbname=radius_dbname,
                user=radius_user,
                password=radius_password,
                sslmode="require"
            )
            cur = conn.cursor()

            sql = "SELECT 1 FROM radcheck WHERE username = %s LIMIT 1;"
            cur.execute(sql, (username,))
            row = cur.fetchone()

            cur.close()
            conn.close()

            return row is None  # True = unique, False = exists

        except Exception as e:
            raise UserError(_("Error %s" % str(e)))




class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    wifi_login = fields.Char(string="WiFi Login")
    wifi_password = fields.Char(string="WiFi Password")



class WiFiPasswordHistory(models.Model):
    _name = "wifi.password.history"
    _description = "WiFi Password History"

    employee_id = fields.Many2one('hr.employee', string="Employee", required=True)
    wifi_login = fields.Char(string="WiFi Login")
    wifi_password = fields.Char(string="WiFi Password")
    login_active_from = fields.Datetime(string='Login Active From', required=True, default=fields.Datetime.now)
    is_removed_from_server = fields.Boolean(string="Is Removed From Server", default=False)






