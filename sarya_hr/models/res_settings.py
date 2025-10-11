# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompanyInherit(models.Model):
    _inherit = "res.company"

    timeoff_resource_calendar_id = fields.Many2one('resource.calendar', string='Default Timeoff Working Hours')


class ResConfigSettingsInherit(models.TransientModel):
    _inherit = 'res.config.settings'

    timeoff_resource_calendar_id = fields.Many2one('resource.calendar', string='Default Timeoff Working Hours', related='company_id.timeoff_resource_calendar_id', readonly=False)
