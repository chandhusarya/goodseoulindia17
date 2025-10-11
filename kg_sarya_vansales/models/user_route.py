# -*- coding: utf-8 -*-

from odoo import models, fields, _


class UserRoute(models.Model):
    _name = 'user.route'
    _description = 'Driver Route'

    name = fields.Char(required=True)
    active = fields.Boolean('Active', default=True)
    customer_count = fields.Integer(compute='_customer_count')
    vehicle_id = fields.Many2one('user.vehicle', 'Vehicle')
    description = fields.Text('Route Details')
    region_lines = fields.One2many('customer.region', 'route_id', 'Regions')

    def _customer_count(self):
        for rec in self:
            customer_count = self.env['res.partner'].search_count([('route_id', '=', rec.id)])
            rec.customer_count = customer_count

    def action_view_customer(self):
        self.ensure_one()
        domain = [
            ('route_id', '=', self.id)]
        return {
            'name': _('Customer'),
            'domain': domain,
            'res_model': 'res.partner',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'context': {'default_route_id': self.id}
        }
