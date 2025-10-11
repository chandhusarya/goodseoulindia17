# -*- coding: utf-8 -*-

from odoo import models, fields


class LoginHistory(models.Model):
    _name = 'user.login.history'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'User Login History'
    _order = 'id desc'

    name = fields.Char(compute='_get_login_name')
    token = fields.Char('Token', copy=False)
    device_id = fields.Char('Device ID')
    user = fields.Many2one('res.users', required=True)
    login_time = fields.Datetime(default=fields.Datetime.now, required=True)
    logout_time = fields.Datetime()
    active = fields.Boolean(default=True)

    def _get_login_name(self):
        for rec in self:
            name = "%s(%s)" % (rec.user.name, rec.login_time)
            rec.name = name
