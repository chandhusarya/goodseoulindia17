# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ClientAsset(models.Model):
    _name = 'client.asset'
    _description = 'Client Asset'
    _order = 'id desc'

    name = fields.Char('Asset', required=True)
    active = fields.Boolean('Active', default=True)
    purchase_date = fields.Date(string='Purchased On')
    lifetime_date = fields.Date(string='Lifetime Date')
    asset_id = fields.Many2one('account.asset', string='Asset', copy=False)
    brand = fields.Char('Brand')
    manufacturer = fields.Char('Manufacturer')
    ref_no = fields.Char('Vendor Bill Ref.')
    vendor = fields.Char('Bought From')
    current_partner_id = fields.Many2one('res.partner', 'Currently Handled By', compute='_compute_current_partner_id')
    asset_move_lines = fields.One2many('client.asset.move', 'client_asset_id', string='Asset Moves')

    @api.depends('asset_move_lines.move_date', 'asset_move_lines.partner_id')
    def _compute_current_partner_id(self):
        for rec in self:
            move = rec.asset_move_lines.sorted('move_date', reverse=True)
            rec.current_partner_id = move[0].partner_id.id if move else False


class ClientAssetMove(models.Model):
    _name = 'client.asset.move'
    _description = 'Client Asset Moves'
    _order = 'move_date desc'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    client_asset_id = fields.Many2one('client.asset', string='Client Asset', required=True)
    move_date = fields.Date('Given On', copy=False, required=True)
