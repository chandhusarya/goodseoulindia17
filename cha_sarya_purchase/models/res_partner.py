# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import api, fields, models, _
from odoo.tools.misc import format_date
from odoo.osv import expression
from datetime import date, datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError, ValidationError
import re

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    unreconciled_aml_vendor_ids = fields.One2many('account.move.line', 'partner_id',
                                           domain=[('reconciled', '=', False),
                                                   ('account_id.deprecated', '=', False),
                                                   ('account_id.account_type', '=', 'liability_payable'),
                                                   ('move_id.state', '=', 'posted')])
    total_due_vendor = fields.Monetary(compute='_compute_for_followup_vendor')
    total_overdue_vendor = fields.Monetary(compute='_compute_for_followup_vendor', string="Overdue Amount")
    port_of_loading = fields.Many2one('purchase.port.of.discharge', string="Port Of Loading")
    delivery_lead_time = fields.Integer("Delivery Lead Time(Hrs)", tracking=True)


    def _compute_for_followup_vendor(self):
        """
        Compute the fields 'total_due', 'total_overdue','followup_level' and 'followup_status'
        """

        today = fields.Date.context_today(self)
        for record in self:
            total_due = 0
            total_overdue = 0
            for aml in record.unreconciled_aml_vendor_ids:
                if aml.company_id == self.env.company:
                    amount = aml.amount_residual
                    total_due += amount
                    is_overdue = today > aml.date_maturity if aml.date_maturity else today > aml.date
                    if is_overdue and not aml.blocked:
                        total_overdue += amount
            record.total_due_vendor = total_due
            record.total_overdue_vendor = total_overdue

    @api.model
    def create(self, vals):
        if (vals.get('customer_rank') and vals.get('customer_rank') > 0) or (vals.get('supplier_rank') and vals.get('supplier_rank') > 0):
            if vals.get('email'):
                match = re.match('^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', vals.get('email'))
                if match == None:
                    raise ValidationError('Not a valid E-mail ID')

            if vals.get('phone') and vals.get('country_id'):
                country = self.env['res.country'].browse(vals.get('country_id'))
                if country.code == 'IN':
                    match = re.match('\\+{0,1}[0-9]{9,12}', vals.get('phone'))
                    if match == None:
                        raise ValidationError('Invalid Phone Number')
        return super(ResPartner, self).create(vals)

    def write(self, values):
        res = super(ResPartner, self).write(values)
        for partner in self:
            if partner.customer_rank > 0 or partner.supplier_rank > 0:
                match = re.match('^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$',
                                 partner.email)
                if match == None:
                    raise ValidationError('Not a valid E-mail ID')

                print("\n\n\n\npartner.country_id      ======>> ", partner.country_id)
                print("partner.country_id.code ======>> ", partner.country_id.code)

                if partner.country_id and partner.country_id.code == 'IN':
                    match = re.match('\\+{0,1}[0-9]{9,12}', partner.phone)
                    if match == None:
                        raise ValidationError('Invalid Phone Number')
        return res
