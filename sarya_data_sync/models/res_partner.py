# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    outlet_code = fields.Char(
        string='Outlet Code',
        copy=False
    )
    is_outlet_customer = fields.Boolean(
        string='Is outlet Customer?',
        copy=False
    )
    local_rec_id = fields.Integer(
        string='Local Record Id',
        copy=False
    )