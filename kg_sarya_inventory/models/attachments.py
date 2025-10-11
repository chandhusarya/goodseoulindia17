# -*- coding: utf-8 -*-

from odoo import models, fields, _


class Attachments(models.Model):
    _inherit = 'partner.attachments'

    shipment_id = fields.Many2one('shipment.advice', string='Shipment Advice')

    bl_id = fields.Many2one('bl.entry', string='BL')
