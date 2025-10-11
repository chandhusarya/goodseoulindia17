# -*- coding: utf-8 -*-

from odoo import models, fields, api


class UserShift(models.Model):
    _name = 'user.shift'
    _description = 'Shift'
    _order = 'date desc, id desc'

    name = fields.Char('Name', compute='_compute_shift_name')
    date = fields.Date('Date', required=True, copy=False, default=fields.Date.context_today)
    user_id = fields.Many2one('res.users', 'Salesperson', required=True, default=lambda self: self.env.user)
    plan_id = fields.Many2one('route.planner', 'Route Planner', copy=False)
    route_id = fields.Many2one(related='plan_id.route_id')
    vehicle_id = fields.Many2one('user.vehicle', 'Van/Vehicle')
    state = fields.Selection(
        string='Status',
        selection=[('draft', 'To be Started'), ('ongoing', 'Ongoing'),
                   ('close', 'Closed'), ],
        required=True, default='draft', copy=False)

    @api.depends('date', 'user_id')
    def _compute_shift_name(self):
        for rec in self:
            name = "%s(%s%s)" % (rec.user_id.name, rec.date, '/' + rec.plan_id.name if rec.plan_id else '')
            rec.name = name



