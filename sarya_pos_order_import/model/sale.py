from odoo import fields, models, api


class SaleOrderInherit(models.Model):
    _inherit = "sale.order"

    pos_import_sales_date = fields.Datetime(string="Order date for Import", copy=False)

    def _prepare_confirmation_values(self):
        values = super()._prepare_confirmation_values()
        if self.pos_import_sales_date:
            values['date_order'] = self.pos_import_sales_date
        return values


class PartnerInherit(models.Model):
    _inherit = "res.partner"


    picking_type_id = fields.Many2one('stock.picking.type')
    journal_id = fields.Many2one('account.journal', string='Sales Journal')
