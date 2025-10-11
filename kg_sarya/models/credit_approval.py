#-*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api
import base64
from odoo.tools.translate import _
import logging
from odoo.exceptions import ValidationError

from odoo import http
from odoo.http import request, content_disposition


class CreditApproval(models.Model):
    _name = 'credit.approval'
    _description = 'Credit Approval'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name')
    user_id = fields.Many2one('res.users', string='Responsible', required=False, default=lambda self: self.env.user)
    partner_id = fields.Many2one(
        'res.partner', string='Customer',
        required=True, change_default=True, index=True, tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",)
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.company)
    date_approval = fields.Date(string='Date', default=fields.Datetime.now)
    credit_limit = fields.Float(string='Credit Limit')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('approve', 'Approved'),
        ], string='Status', readonly=True, copy=False, index=True, tracking=True, default='draft')

    @api.model
    def create(self, vals):
        res = super(CreditApproval, self).create(vals)
        res.name = str(res.partner_id.name) + ' - Credit Approval'
        return res

    def action_approve(self):
        if self.partner_id.parent_customer_id:
            if self.partner_id.child_credit_limit == 0.00:
                parent_credit_limit = self.partner_id.parent_customer_id.credit_limit
                child_credit_total = self.partner_id.parent_customer_id.child_credit_total
                if (child_credit_total+self.credit_limit)>parent_credit_limit:
                    raise ValidationError('Total of child customer credit limit should not be greater parent customer credit limit...')
                else:
                    self.state = 'approve'
                    self.partner_id.parent_customer_id.child_credit_total = child_credit_total + self.credit_limit
                    self.partner_id.child_credit_limit = self.credit_limit
            else:
                raise ValidationError('Credit Limit Already set for this Company')
        else:
            raise ValidationError('No Parent customer for this Company') 

