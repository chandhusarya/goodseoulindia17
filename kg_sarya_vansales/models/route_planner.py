# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
import base64
import io
import csv


class RoutePlanner(models.Model):
    _name = "route.planner"
    _description = "Route Planner"
    _inherit = ['mail.thread']
    _order = "name desc"

    name = fields.Char('Name', required=True)
    active = fields.Boolean('Active', default=True)
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', string='Plan Manager', default=lambda self: self.env.user)
    route_id = fields.Many2one('user.route', string='Route', required=True)
    date_from = fields.Date('Valid From')
    date_to = fields.Date('Valid To')
    child_ids = fields.One2many('route.planner.line', 'plan_id', string='Routes')

    import_file = fields.Binary(string='File to import route Plan')
    import_filename = fields.Char(string='File Name', help="Name of the export file generated for this batch",
                                  store=True, copy=False)

    note = fields.Text('Note')
    import_remarks = fields.Text('Import Remark')

    @api.constrains('date_from', 'date_to', 'user_id')
    def _check_date(self):
        for planner in self.filtered('user_id'):
            domain = [
                ('date_from', '<', planner.date_to),
                ('date_to', '>', planner.date_from),
                ('user_id', '=', planner.user_id.id),
                ('id', '!=', planner.id),
            ]
            planners = self.search_count(domain)
            if planners:
                raise ValidationError(
                    _('You cannot have 2 route planners that overlap on the same dates for the same salesperson.'))


    def import_route(self):
        csv_data = base64.b64decode(self.import_file)
        data_file = io.StringIO(csv_data.decode("utf-8"))
        data_file.seek(0)
        reader = csv.DictReader(data_file)
        result = []
        route_mapping = {}
        for row in reader:
            customer = False
            for column in row:
                column = column.strip()
                print("column ==>> ", column)
                print("row ======>> ", row.get(column, False))
                if column in ('Customer', '﻿Customer'):
                    customer_name_split = row[column].split('?')           
                    customer_name = customer_name_split[0].strip()
                    try:
                        cust_sequence = customer_name_split[1].strip()
                    except Exception as e:
                        raise ValueError('"%s", %s, %s' % (ustr(e), column, row[column]))

                    customer = self.env['res.partner'].search([('cust_sequence', '=', cust_sequence)])
                    if len(customer) > 1:
                        result.append(customer_name)
                    if not customer:
                        result.append(customer_name)

                elif row.get(column, False):
                    print("customer ====>> ", customer)
                    if customer:
                        route_date = datetime.strptime(column, '%d/%m/%Y')
                        if route_date not in route_mapping:
                            route_mapping[route_date] = {
                                'customer' : [customer.id]
                            }
                        else:
                            route_mapping[route_date]['customer'].append(customer.id)

        count = 0
        for date in route_mapping:
            count += 1
            vals = {
                'route_date' : date,
                'partner_ids' : route_mapping[date]['customer'],
                'plan_id' : self.id
            }
            self.env['route.planner.line'].create(vals)

        message = ""
        if result:
            message = "Please check below customers and configure manually "
            for customer_name in result:
                message = "%s, %s" % (message, customer_name)

        self.import_remarks = message

    def update_sale_todays_vansales_person(self):

        #Clear all customer
        all_customer = self.env['res.partner'].search([])
        for customer in all_customer:
            customer.todays_vansales_route_user = False

        current_date = fields.Date.context_today(self)
        # weekday = str(current_date.weekday())
        domain = [('route_date', '=', current_date)]
        route_planner = self.env['route.planner.line'].sudo().search(domain)
        for plan in route_planner:
            driver = plan.plan_id.route_id.vehicle_id.driver_id
            if driver:
                for customer in plan.partner_ids:
                    customer.todays_vansales_route_user = driver
                    customer.vansales_visit_status = 'pending'

        route_planner = self.env['route.planner.line'].sudo().search([])
        for plan in route_planner:
            driver = plan.plan_id.route_id.vehicle_id.driver_id
            if driver:
                for customer in plan.partner_ids:
                    customer.vansales_person = driver


class RoutePlannerLine(models.Model):
    _name = "route.planner.line"
    _description = "Route Planner Routes"
    _rec_name = "plan_id"

    _order = "route_date asc"

    name = fields.Char(compute='_get_name')
    weekday = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday'),
    ], string='Week Day')

    route_date = fields.Date("Date")

    plan_id = fields.Many2one('route.planner', required=True, ondelete='cascade')
    route_id = fields.Many2one(related='plan_id.route_id')
    user_ids = fields.Many2many('res.users', string='Salespersons')
    partner_ids = fields.Many2many('res.partner', string='Customers', domain="[('route_id', '=', route_id)]")

    @api.depends('plan_id', 'weekday')
    def _get_name(self):
        for rec in self:
            name = rec.name + '/' + dict(rec._fields['weekday'].selection).get(rec.weekday)
            rec.name = name

    @api.constrains('weekday')
    def _check_weekday(self):
        for rec in self:
            weeks = rec.plan_id.child_ids.mapped('weekday')
            print(weeks)
            print(set(weeks))
            if len(weeks) != len(set(weeks)):
                raise ValidationError(
                    _("Same week day cannot have more than one for the planner %s.") % rec.plan_id.name)
