# -*- coding: utf-8 -*-

from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _description = 'Customer Route Details'

    route_id = fields.Many2one('user.route', string="Route")
    shift_id = fields.Many2one('user.shift', string="Driver Route", copy=False,
                               help='Shift of the related salesman when this customer is created')

    # overrides the field from kg_sarya module to add domain
    region = fields.Many2one('customer.region', string='Region', domain="[('route_id', '=', route_id)]")
    visit_log_lines = fields.One2many('customer.visit.log', 'partner_id', string='Visit Log', copy=False)

    _sql_constraints = [
        ('check_name', "CHECK( (type='contact' AND name IS NOT NULL) or (type!='contact') )", 'Contacts require a name'),
    ]

    def write(self, vals):
        """Route-Driver change in log"""
        if 'route_id' in vals.keys():
            user_route = self.env['user.route'].search([('id', '=', vals.get('route_id'))])
            if self.route_id:
                note = 'Driver-Route Changed from ' + self.route_id.name + ' to ' + user_route.name
            else:
                note = 'Assigned Driver-Route ' + str(user_route.name)
            self.sudo().activity_schedule(
                'kg_sarya_vansales.mail_driver_change',
                note=note,
                user_id=self.env.user.id)
        res = super(ResPartner, self).write(vals)
        return res

    def is_visited(self, visit_date=False):
        if not visit_date:
            visit_date = fields.Datetime.now()
        log_ids = self.visit_log_lines.filtered(lambda log: log.visit_date.date() == visit_date.date())
        return True if log_ids else False

    def remove_visit_log(self, visit_date):
        log_ids = self.visit_log_lines.filtered(lambda log: log.visit_date_time == visit_date)
        return log_ids.write({
            'active': False
        })


