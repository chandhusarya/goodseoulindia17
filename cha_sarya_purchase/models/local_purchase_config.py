from odoo import fields, models

class LocalPurchaseConfig(models.Model):
    _name = 'local.purchase.config'
    _description = 'Local Purchase Configuration'

    name = fields.Char(string="Name", required=True)
    operation_type_id = fields.Many2one(
        'stock.picking.type', 
        string="Operation Type", 
        domain=[('code', '=', 'incoming')]
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account', 
        string="Analytic Account"
    )
