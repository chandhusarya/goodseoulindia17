from odoo import models, fields, api

class HrTaxConfig(models.Model):
    _name = 'hr.tax.config'
    _description = 'Tax Configuration'
    _rec_name = 'financial_year'

    financial_year = fields.Char(string="Financial Year", required=True)
    tax_regime = fields.Selection([('old', 'Old'), ('new', 'New')])
    standard_deduction = fields.Integer(
        string='Standard Deduction'
    )
    tax_rebate = fields.Integer(
        string='Tax Rebate Limit'
    )
    line_ids = fields.One2many('hr.tax.config.line', 'config_id', string="Slabs")

    @api.depends('financial_year', 'tax_regime')
    def _compute_display_name(self):
        for config in self:
            config.display_name = f"{config.financial_year} ({config.tax_regime})"


class HrTaxConfigLine(models.Model):
    _name = 'hr.tax.config.line'
    _description = 'Tax Configuration Line'
    _order = 'lower_limit asc'

    config_id = fields.Many2one('hr.tax.config', string="Configuration", required=True, ondelete='cascade')
    lower_limit = fields.Monetary(string="Lower Limit", required=True)
    upper_limit = fields.Monetary(string="Upper Limit", help="Leave empty for no upper limit")
    rate = fields.Float(string="Tax Rate (%)", required=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

