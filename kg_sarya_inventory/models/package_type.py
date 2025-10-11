# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class PackageTypeInherit(models.Model):
    _inherit = 'stock.package.type'

    short_code = fields.Char(string="short Code ", store=True)

