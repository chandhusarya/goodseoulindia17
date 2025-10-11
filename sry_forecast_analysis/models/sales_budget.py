from odoo import models, fields, api, _
import datetime
from datetime import datetime
from odoo.exceptions import ValidationError, UserError
import base64
import io
import csv

MONTH_SELECTION = [
    ('01', 'January'),
    ('02', 'February'),
    ('03', 'March'),
    ('04', 'April'),
    ('05', 'May'),
    ('06', 'June'),
    ('07', 'July'),
    ('08', 'August'),
    ('09', 'September'),
    ('10', 'October'),
    ('11', 'November'),
    ('12', 'December')
]

YEAR_SELECTION = [
    ('2022', '2022'),
    ('2023', '2023'),
    ('2024', '2024'),
    ('2025', '2025'),
    ('2026', '2026'),
    ('2027', '2027'),
    ('2028', '2028'),
    ('2029', '2029'),
    ('2030', '2030'),
    ('2031', '2031'),
    ('2032', '2032'),
    ('2033', '2033'),
]

STATE_SELECTION = [
    ('draft', 'Draft'),
    ('confirm', 'Confirm'),
    ('cancel', 'Cancel'),
]

class sryStockBudget(models.Model):
    _name = 'sry.sales.budget'
    _description = 'Sales Budget'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    year = fields.Selection(YEAR_SELECTION, string='Year', required=True, copy=False)
    month = fields.Selection(MONTH_SELECTION, string='Month', required=True, copy=False)
    state = fields.Selection(STATE_SELECTION, string='Status', readonly=True, copy=False, default='draft', tracking=True)
    budget_line = fields.One2many('sry.sales.budget.line', 'budget_id', string='Budget Line')
    import_file = fields.Binary(string='IMPORT')
    import_filename = fields.Char(string='File Name', store=True, copy=False)

    def create_import_template(self):
        return self.env.ref('sry_forecast_analysis.sry_sales_budget_import_template').report_action(self)

    def button_confirm(self):
        pass

    def button_cancel(self):
        pass

    def import_data_from_csv(self):
        self.budget_line.unlink()

        csv_data = base64.b64decode(self.import_file)
        data_file = io.StringIO(csv_data.decode("unicode_escape"))
        data_file.seek(0)
        reader = csv.DictReader(data_file)
        result = []
        for row in reader:
            if 'Quantity' in row and row['Quantity']:
                cleaned_row = {key.strip('ï»¿'): value for key, value in row.items()}
                cleaned_row.update({'budget_id': self.id})
                result.append(cleaned_row)
        self.env['sry.sales.budget.line'].create(result)

class sryStockBudgetLine(models.Model):
    _name = 'sry.sales.budget.line'
    _description = 'Sales Budget Line'


    budget_id = fields.Many2one('sry.sales.budget', string='Sales Budget', required=True, ondelete='cascade', index=True, copy=False)
    # customer_id = fields.Many2one('res.partner', string='Customer')
    master_parent_id = fields.Many2one('master.parent', string='Master Parent')
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Integer(string='Quantity')
    budget_year = fields.Selection(related='budget_id.year', string='Year', copy=False, store=True)
    budget_month = fields.Selection(related='budget_id.month', string='Month', copy=False, store=True)
    trade_channel_id = fields.Many2one('trade.channel',string='Trade Channel',compute='_compute_trade_channel', store=True)

    @api.depends('master_parent_id')
    def _compute_trade_channel(self):
        for rec in self:
            partner = self.env['res.partner'].search([('master_parent_id', '=', rec.master_parent_id.id)], limit=1)
            if partner:
                rec.trade_channel_id = partner.trade_channel.id
