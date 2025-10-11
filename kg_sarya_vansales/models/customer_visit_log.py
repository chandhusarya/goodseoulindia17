# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CustomerVisitLog(models.Model):
    _name = 'customer.visit.log'
    _description = 'Customer Visit Log'
    _order = 'id desc'

    name = fields.Char(compute='_get_visit_name')
    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade', string='Customer')
    user_id = fields.Many2one('res.users', required=True, ondelete='cascade', string='Salesperson')
    visit_date_time = fields.Datetime(default=fields.Datetime.now, required=True, copy=False)
    visit_date = fields.Datetime(compute='_compute_visit_date', store=True)
    remarks = fields.Text('Remarks', copy=False)
    vehicle_no = fields.Char('Van No.')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('visit_uniq', 'unique (partner_id,visit_date,user_id,active)', 'This customer is already marked as visited!')
    ]

    @api.depends('visit_date_time')
    def _compute_visit_date(self):
        for rec in self:
            rec.visit_date = rec.visit_date_time.date()

    @api.depends('partner_id', 'visit_date')
    def _get_visit_name(self):
        for rec in self:
            name = "%s(%s)" % (rec.partner_id.name, rec.visit_date)
            rec.name = name
