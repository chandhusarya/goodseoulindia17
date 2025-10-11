from odoo import models, fields, api
from odoo.tools import float_is_zero


class RebateReportWizard(models.TransientModel):
    _name = 'rebate.report.wizard'
    _rec_name = 'partner_id'
    _description = 'Rebate Report'

    partner_id = fields.Many2one('res.partner', 'Customer', required=True)
    rebate_ids = fields.Many2many('rebate.master', string='Rebates')
    report_type = fields.Selection(
        string='Report Type',
        selection=[('simple', 'Simplified'),
                   ('detailed', 'Detailed'), ],
        required=True, default='simple')
    date_start = fields.Date('Start Date')
    date_end = fields.Date('End Date')
    include_reserve = fields.Boolean('Include reserved', default=False)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        rebates = self.partner_id.property_product_pricelist.rebate_ids
        self.update({
            'rebate_ids': [(6, 0, rebates.ids)],
        })

    def _get_rebate_simplified_values(self, rebate_ids):
        # get combination of partner > rebate
        if not rebate_ids:
            return []
        values = []
        ss = self.partner_id
        for rebate in rebate_ids:
            date_end = self.date_end or rebate.date_end
            FixedRebate = self.env['rebate.fixed.item'].sudo()
            invoice_amount = self.partner_id._get_rebase_invoice_total(date_from=rebate.date_start,
                                                                       date_to=date_end)
            rebate_values = self.partner_id._get_rebate_values(rebate, invoice_amount)
            is_reservation = rebate_values.get('progressive_type', '') == 'reservation'
            if is_reservation and not self.include_reserve:
                continue
            progressive_slab = rebate_values.get('progressive_slab', False)
            fixed_vals = []
            fix_rebates = rebate_values.get('fixed_rebate_vals', False)
            for fr in fix_rebates:
                fixed_id = FixedRebate.browse(fr)
                fixed_vals.append({
                    'fixed_rebate': fixed_id.description,
                    'fixed_rebate_percentage': fixed_id.percentage,
                    'amount': fix_rebates[fr],
                })
            values.append({
                'rebate': rebate.name,
                'progressive_rebate': progressive_slab.slab or '',
                'progressive_amount': rebate_values.get('progressive_amount', 0.0),
                'progressive_type': rebate_values.get('progressive_type', ''),
                'invoiced_amount': invoice_amount,
                'fixed_rebate_total': rebate_values.get('fixed_rebate_total', 0.0),
                'fixed_rebates': fixed_vals,
            })
        return values

    def _get_rebate_detailed_values(self, rebates):
        # get combination of partner > rebate > invoice_line
        """TODO: FIX: fetching invoice total with invoice_date.
        """
        AccountMove = self.env['account.move']
        Product = self.env['product.product']
        rebate_vals = {}
        for rebate in rebates:
            date_end = self.date_end or rebate.date_end
            invoice_values = self.partner_id._get_rebase_invoice_values(date_from=rebate.date_start,
                                                                        date_to=date_end)
            for inv_value in invoice_values:
                move_id = AccountMove.browse(inv_value['move_id'][0])
                if move_id.move_type in ('out_invoice', 'out_refund'):
                    product = Product.browse(inv_value['product_id'][0])
                    price_total = inv_value['price_total']
                    # convert to company currency if needed
                    if rebate.product_type == 'selected':
                        if product.section.id not in rebate.customer_section_ids.ids \
                                and product.brand.id not in rebate.brand_id.ids:
                            pass
                    sign = -1 if move_id.move_type == 'out_refund' else 1
                    fixed_rebate_amount = (rebate.total_without_progressive * price_total) / 100

                    # check progressive slab
                    previous_invoice_amount = self.partner_id._get_rebase_invoice_total(date_from=rebate.date_start,
                                                                                        date_to=move_id.date, )
                    progressive_slab, item_type = self.partner_id._get_progressive_rebate_slab(rebate,
                                                                                               previous_invoice_amount)
                    is_reservation = item_type == 'reservation'
                    if is_reservation and not self.include_reserve:
                        continue
                    progressive_amount = (progressive_slab.rebate_percentage * price_total) / 100
                    fixed_vals = []
                    for line in rebate.fixed_ids:
                        reb_amount = (line.percentage * price_total) / 100
                        fixed_vals.append({
                            'fixed_rebate': line.description,
                            'fixed_rebate_percentage': line.percentage,
                            'amount': reb_amount,
                        })
                    data = {
                        'rebate': rebate.name,
                        'invoice': move_id.name,
                        'partner': inv_value['partner_id'][1],
                        'total_invoice': price_total,
                        'progressive_rebate_percentage': progressive_slab.rebate_percentage or 0.0,
                        'fixed_rebate_percentage': rebate.total_without_progressive,
                        'fixed_rebate_amount': sign * fixed_rebate_amount or 0.0,
                        'progressive_rebate_amount': sign * progressive_amount or 0.0,
                        'progressive_rebate': progressive_slab and progressive_slab.slab or '',
                        'product': product.name,
                        'item_type': item_type,
                        'fixed_rebates': fixed_vals,
                    }
                    # group by rebate
                    if rebate.id in rebate_vals:
                        rebate_vals[rebate.id].append(data)
                    else:
                        rebate_vals[rebate.id] = [data]
        return rebate_vals

    def _get_common_report_values(self):
        return {
            'report_date': fields.Date.context_today(self),
            'company_currency_id': self.env.company.currency_id,
        }

    def _prepare_simple_rebate_report(self):
        rebate_ids = self.rebate_ids
        if not rebate_ids:
            rebate_ids = self.partner_id.property_product_pricelist.rebate_ids
        rebates = self._get_rebate_simplified_values(rebate_ids)
        data = self._get_common_report_values()
        data.update({
            'rebates': rebates,
        })
        return data

    def _prepare_detailed_rebate_report(self):
        rebate_ids = self.rebate_ids
        if not rebate_ids:
            rebate_ids = self.partner_id.property_product_pricelist.rebate_ids
        rebate_vals = self._get_rebate_detailed_values(rebate_ids)
        data = self._get_common_report_values()
        data.update({
            'rebate_vals': rebate_vals,
            'rebate_ids': rebate_ids.ids,
        })
        return data

    def generate_report(self):
        report_name = 'kg_sarya_rebate.rebate_pdf_report_simplified' \
            if self.report_type == 'simple' else 'kg_sarya_rebate.rebate_pdf_report_detailed'
        return self.env.ref(report_name).report_action(self)
