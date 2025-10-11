from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    fssai_no = fields.Char(
        string='FSSAI No.')
    property_account_payable_id = fields.Many2one('account.account', company_dependent=True,
        string="Account Payable",
        domain="['|', ('account_type', '=', 'liability_payable'), ('account_type', '=', 'asset_receivable'), ('deprecated', '=', False)]",
        help="This account will be used instead of the default one as the payable account for the current partner",
        required=True)#('account_type', '=', 'liability_payable'),
    delivery_contact = fields.Char(string='Delivery Contact')

