# -*- coding: utf-8 -*-

from odoo import models, fields


class ReasonCode(models.Model):
    _name = 'sales.return.reason.code'
    _description = 'Reason Code'
    _rec_name = 'code'
    _order = 'id desc'

    name = fields.Char('Reason', required=True)
    code = fields.Char('Code', required=True)
    stock_type = fields.Selection(string='Default Stock (IN/OUT)', selection=[('in', 'In'), ('out', 'Out'), ],
                                  default='in', required=True)
    description = fields.Char('Description')
    move_to_nonsaleable = fields.Boolean('Items in None saleable Location (Van Sales)')

    def name_get(self):
        res = []
        for rec in self:
            name = "[%s] %s" % (rec.code, rec.name)
            res += [(rec.id, name)]
        return res
