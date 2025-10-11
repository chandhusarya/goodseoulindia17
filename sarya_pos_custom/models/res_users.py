from odoo import fields, models, api



class ResUsersPOSAllowed(models.Model):
    _name = 'res.users.pos.allowed'
    _description = 'Allowed POS per Company'
    _rec_name = 'pos_config_id'

    user_ids = fields.Many2many('res.users', required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    pos_config_id = fields.Many2one('pos.config', required=True)







class ResUsers(models.Model):
    """ADD restrict POS buttons in the user form"""
    _inherit = 'res.users'

    '''
    Not using because of multi company issue
    '''
    allowed_pos = fields.Many2many(
        comodel_name='pos.config',
        string='Allowed Pos',
        help='Allowed Pos for this user'
    )
    '''
    End of not using because of multi company issue
    '''


    show_users = fields.Boolean(
        string="Show users of pos",
        default=True,
        help='Show users in dashboard for pos administrators only'
    )

    def get_allowed_pos_for_current_company(self):
        """Return only POS configs allowed for the current company."""
        confs  = self.env['res.users.pos.allowed'].search([
                    ('company_id', '=', self.env.company.id),
                    ('user_ids', 'in', self.id)
                ]).mapped('pos_config_id')
        return confs