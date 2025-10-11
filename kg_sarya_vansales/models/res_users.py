# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    is_driver = fields.Boolean('res.users')


    def _update_login_history(self, token):
        login_history = self.env['user.login.history'].sudo().search(
            [('user', '=', self.id), ('token', '=', token), ('logout_time', '=', False)], limit=1,
            order='login_time desc')
        if login_history:
            login_history.write({
                'logout_time': fields.Datetime.now()
            })

    def customer_count(self,route_id):
        if route_id:
            count = self.env['res.partner'].search_count([('route_id', '=', route_id.id)])
            return count
        else:
            return 0



    def _create_login_history(self, token, device_id):
        self._update_login_history(token=token)
        vals = {
            'token': token,
            'user': self.id,
            'device_id': device_id,
        }
        self.env['user.login.history'].sudo().create(vals)

    def _get_active_route_plan(self, route_date=False):
        """returns the current active plan for the logged-in user.
            if multiple plans found, returns the firt matching one."""

        current_date = route_date or fields.Date.context_today(self)
        weekday = str(current_date.weekday())
        domain = [('plan_id.date_from', '<=', current_date),
                  ('plan_id.date_to', '>=', current_date), ('weekday', '=', weekday)]
        user_wise_domain = domain + [('user_ids', 'in', self.ids)]
        planner_id = self.env['route.planner.line'].sudo().search(user_wise_domain, limit=1)
        if not planner_id:
            customers = self.env['res.partner'].sudo().search([('user_id', '=', self.id)])
            customer_wise_domain = domain + [('partner_ids', 'in', customers.ids)]
            planner_id = self.env['route.planner.line'].sudo().search(customer_wise_domain, limit=1)
        return planner_id

    def _get_active_shift(self, shift_date=False, create_if_not=False):
        domain = [('user_id', '=', self.id), ('state', '=', 'ongoing')]
        if shift_date:
            domain += [('date', '=', shift_date)]
        else:
            domain += [('date', '=', fields.Date.context_today(self))]
        shift_id = self.env['user.shift'].sudo().search(domain, limit=1, order='date')
        if not shift_id and create_if_not:
            shift_id = self._create_shift()
        return shift_id


    def _create_shift(self):
        """Creates a shift_id for the user on the fly if there is no active shift for the logged user."""
        self._close_shift()
        plan = self._get_active_route_plan()
        values = {
            'user_id': self.id,
            'plan_id': plan.plan_id.id,
            'state': 'ongoing',
        }
        shift_id = self.env['user.shift'].sudo().create(values)
        return shift_id

    def _close_shift(self):
        domain = [('user_id', '=', self.id), ('state', '=', 'ongoing')]
        shift_ids = self.env['user.shift'].sudo().search(domain)
        shift_ids.write({
            'state': 'close'
        })
