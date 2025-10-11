# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class RebateRealTime(models.Model):
    _name = "prg.rebate.realtime"

    rebate_id = fields.Many2one('rebate.master')
    partner_id = fields.Many2one('res.partner')
    current_sale_amount = fields.Float()
    total_sale = fields.Float()
    slab_reach = fields.Float()
    rebate_applied = fields.Float()
    rebate_updated = fields.Float()
    sale_order = fields.Many2one('sale.order')
    date = fields.Date()
    rebate_amount = fields.Float()
    state = fields.Selection([('posted','Posted'),('cancel','Cancel')],default='posted')
    move_id = fields.Many2one('account.move')
    child_partner = fields.Many2one('res.partner')

