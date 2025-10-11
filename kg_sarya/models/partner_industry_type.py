#-*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api
import base64
from odoo.tools.translate import _
import logging
from odoo.exceptions import ValidationError

from odoo import http
from odoo.http import request, content_disposition


class PartnerIndustryType(models.Model):
    _name = 'partner.industry.type'
    _description = 'Customer Industry Type'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name')
