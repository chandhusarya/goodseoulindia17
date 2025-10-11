# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CustomerSubClass(models.Model):
    _name = 'master.parent'
    _description = 'Customer Master Parent'
    _rec_name = 'name'

    name = fields.Char(string="Name")
    block_if_over_due = fields.Boolean("Block SO If Over-Due")


class ResPartnerInherit(models.Model):
    _inherit = 'res.partner'

    master_parent_id = fields.Many2one('master.parent', string="Master Parent")
