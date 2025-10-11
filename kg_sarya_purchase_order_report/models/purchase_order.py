from odoo import models, fields, api

class PurchaseOrderReport(models.Model):
    _inherit = 'purchase.order'

    amount_in_words = fields.Char(required=False, compute="_amount_in_word")

    @api.depends('amount_total')
    def _amount_in_word(self):
        for rec in self:
            rec.amount_in_words = str(rec.currency_id.amount_to_text(rec.amount_total)).upper()


class PurchaseOrderInstruction(models.Model):
    _inherit = 'res.company'

    purchase_special_instruction=fields.Html(string='Purchase Order Instruction')
