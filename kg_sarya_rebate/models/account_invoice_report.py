
from odoo import models, fields, api

class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'

    @api.model
    def _from(self):
        return '''
                FROM account_move_line line
                    LEFT JOIN res_partner partner ON partner.id = line.partner_id
                    LEFT JOIN product_product product ON product.id = line.product_id
                    LEFT JOIN account_account account ON account.id = line.account_id
                    LEFT JOIN product_template template ON template.id = product.product_tmpl_id
                    LEFT JOIN uom_uom uom_line ON uom_line.id = line.product_uom_id
                    LEFT JOIN uom_uom uom_template ON uom_template.id = template.uom_id
                    INNER JOIN account_move move ON move.id = line.move_id
                    LEFT JOIN res_partner commercial_partner ON commercial_partner.id = move.commercial_partner_id
                    LEFT JOIN ir_property product_standard_price
                        ON product_standard_price.res_id = CONCAT('product.product,', product.id)
                        AND product_standard_price.name = 'standard_price'
                        AND product_standard_price.company_id = line.company_id
                    JOIN {currency_table} ON currency_table.company_id = line.company_id
            '''.format(
            currency_table=self.env['res.currency']._get_query_currency_table(self.env.companies.ids,
                                                                              fields.Date.today())
        )

