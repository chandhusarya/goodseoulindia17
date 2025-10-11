# -*- coding: utf-8 -*-

from odoo import fields, models
from ast import literal_eval


class PurchaseSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    wms_partner_id = fields.Many2many('res.partner', string='Partner')

    def set_values(self):       
        res = super(PurchaseSettings, self).set_values()       
        self.env['ir.config_parameter'].sudo().set_param('many2many.wms_partner_id', self.wms_partner_id.ids)       
        return res
  
    def get_values(self):       
        res = super(PurchaseSettings, self).get_values()       
        with_user = self.env['ir.config_parameter'].sudo()      
        com_partner = with_user.get_param('many2many.wms_partner_id')       
        res.update(wms_partner_id=[(6, 0, literal_eval(com_partner))] if com_partner else False,       )       
        return res

