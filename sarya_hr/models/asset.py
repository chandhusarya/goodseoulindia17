from odoo import fields, models, api, _
from datetime import datetime


class AssetMaster(models.Model):
    _name = 'asset.master'
    _description = 'Asset Master'
    _inherit = ['mail.thread']

    _sql_constraints = [
        ('unique_code', 'unique (code)',
         'Asset Code unique for each Asset.')
    ]

    name = fields.Char(string="Name", copy=False, tracking=True)
    code = fields.Char(string="Asset ID", copy=False, tracking=True,readonly=False)
    serial_number = fields.Char(string="Serial Number")
    active = fields.Boolean(default=True, copy=False)
    is_consume = fields.Boolean(default=False, copy=False, string="Is consumed?")
    history_ids = fields.One2many('asset.history', 'asset_id', string="Asset History")
    asset_account_id = fields.Many2one('account.asset', string="Asset Account", copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'active')], default='draft', string="State")
    is_allocated = fields.Boolean(default=False, copy=False, readonly=True, store=True)
    is_active = fields.Boolean(string="Active", default=True)
    asset_category_id = fields.Many2one('asset.category', string='Asset Category')
    account_asset_id = fields.Many2one(
        comodel_name='account.asset',
        string='Account Asset')
    is_vehicle = fields.Boolean('Is Vehicle', related='asset_category_id.is_vehicle')

    # Vehicle
    # brand_id = fields.Many2one('sar.vehicle.model.brand', 'Vehicle Manufacturer')
    # model_id = fields.Many2one('sar.vehicle.model', 'Vehicle Model')
    chasis_no = fields.Char('Chasis No.')
    engine_no = fields.Char('Engine No.')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company', default=lambda self: self.env.company)


    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, order=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('code', operator, name)]
        return self._search(domain + args, limit=limit, order=order)

    def name_get(self):
        result =[]
        for record in self:
            result.append((record.id,record.name+"["+str(record.code)+']'))
        return result


    def open_history(self):
        return{
            'name': 'Asset History',
            'view_mode': 'tree,form',
            'view_id': False,
            'res_model': 'asset.history',
            'context': {'search_default_asset_id': self.id},
            'domain': [('id', 'in', self.history_ids.ids)],
            'type': 'ir.actions.act_window',
        }

    @api.model
    def create(self, vals):
        vals['code'] = self.env['ir.sequence'].next_by_code('asset.master') or _('New')
        res = super(AssetMaster, self).create(vals)
        return res
