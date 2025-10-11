from odoo import fields, models, api


class POSConf(models.Model):
    _inherit = 'pos.config'

    lpo_picking_type_id = fields.Many2one(comodel_name='stock.picking.type', string='LPO Picking Type')
    # allowed_users_ids = fields.Many2many('res.users', string='Allowed Users', help="Users allowed to access this POS requests(Wastage & Stock Adjustment).")
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', help="Analytic account to be used for this POS.")
    terminal_type = fields.Selection(
        string='Terminal Type',
        selection=[('primary', 'Primary Terminal'),
                   ('additional', 'Additional Terminal'), ],
        required=True, )

    allowed_users = fields.Many2many(
        comodel_name='res.users',
        string='Allowed Users',
        help='Which shows the specified pos for '
             'particular user',
        compute='_compute_allowed_users', store=False
    )

    # @api.depends_context('company')
    # def _compute_allowed_users(self):
    #     # computes the allowed users in pos
    #     for rec in self:
    #         print("Computing allowed users for POS config:", rec.name)
    #         # checks is show_users is ticked in user settings
    #         if rec.env.user.show_users:
    #             rec.allowed_users = self.env['res.users'].search(
    #                 [('allowed_pos', '=', rec.id), ('company_id', '=', self.env.company.id)])
    #         else:
    #             rec.allowed_users = None
    @api.depends_context('company')
    def _compute_allowed_users(self):
        current_company = self.env.company
        Allowed = self.env['res.users.pos.allowed']

        for rec in self:
            if self.env.user.show_users:
                # Find mappings for this POS config in current company
                mappings = Allowed.search([
                    ('company_id', '=', current_company.id),
                    ('pos_config_id', '=', rec.id)
                ])
                for u in mappings.mapped('user_ids'):
                    print("User:", u.name)
                rec.allowed_users = mappings.mapped('user_ids')
            else:
                rec.allowed_users = False


    def action_inventory_transfers(self):
        picking_type_id = self.picking_type_id
        location_src = picking_type_id.default_location_src_id
        pickings = self.env['stock.picking'].search(['|', ('location_id', '=', location_src.id),
                                                     ('location_dest_id', '=', location_src.id)])
        return {
            'name': 'Transfers',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'context': {'create': False},
            'domain': [('id', 'in', pickings.ids)],
            'target': 'current'
        }


    def action_Local_purchase(self):
        return {
            'name': 'Local Purchase',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'local.purchase',
            'context': {'create': False, 'default_pos_id':self.id},
            'domain': [('pos_id', '=', self.id)],
            'target': 'current'
        }
