import logging

from odoo import models, fields, _, api
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare
from datetime import date, timedelta

_logger = logging.getLogger(__name__)

class RebateMoveWizard(models.TransientModel):
    _name = 'rebate.move.wizard'
    _rec_name = 'partner_id'
    _description = 'Create Journal Entries for Rebate'

    def _get_move_entry_date(self):
        today = fields.Date.today()
        if today.day <= 10:
            prev = today.replace(day=1) - timedelta(days=1)
            return prev
        return today

    partner_id = fields.Many2one('res.partner', 'Customer')
    from_date = fields.Date('From')
    to_date = fields.Date('To')
    move_date = fields.Date('Journal Entry Date', default=_get_move_entry_date)
    rebate_ids = fields.Many2many('rebate.master', string='Rebates')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        rebates = self.partner_id.property_product_pricelist.rebate_ids
        self.update({
            'rebate_ids': [(6, 0, rebates.ids)],
        })

    # def create_move(self):
    #     domain = []
    #     if self.partner_id:
    #         domain += [('partner_id', '=', self.partner_id.id)]
    #     if self.rebate_ids:
    #         domain += [('rebate_id', 'in', self.rebate_ids.ids)]
    #     entries = self.env['rebate.entry'].search(domain)
    #     new_move_lines = entries._create_progressive_rebate_account_move(move_date=self.move_date, is_auto=False)
    #     if new_move_lines:
    #         action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_moves_all_a')
    #         ids = new_move_lines.ids
    #         action['domain'] = [('id', 'in', ids)]
    #         return action

    def create_move(self):
        domain = []
        if self.partner_id:
            domain += [('partner_id', '=', self.partner_id.id)]


        if self.rebate_ids:
            rebate_ids = self.rebate_ids
        else:
            rebate_ids = self.env['rebate.master'].search([])


        for rebate in rebate_ids:
            if rebate.progressive_ids:
                total_return_value = 0
                total_invoice_value = 0
                all_price_list = self.env['product.pricelist'].search([('rebate_ids', 'in', rebate.id)])
                print("rebate ==>> ", rebate)
                print("from_date ==>> ", self.from_date)
                print("to_date ==>> ", self.to_date)
                for price_list in all_price_list:

                    partner_list = []
                    partner_list_all = self.env['res.partner'].search([])

                    for partner in partner_list_all:
                        if partner.property_product_pricelist.id == price_list.id:
                            partner_list.append(partner.id)

                    invoice_value = self.get_invoice_value(rebate, price_list, partner_list)
                    if invoice_value:
                        total_invoice_value = total_invoice_value + invoice_value
                    return_value = self.get_credit_note_value(rebate, price_list, partner_list)
                    if return_value:
                        total_return_value = total_return_value + return_value



                print("total_invoice_value ==>> ", total_invoice_value)
                print("total_return_value  ==>> ", total_return_value)

                if not rebate.is_rebate_computed_on_untaxed:
                    total_invoice_value = total_invoice_value + total_invoice_value * 0.05
                    total_return_value = total_return_value + total_return_value * 0.05

                total_amount = total_invoice_value - total_return_value

                print("total_invoice_value vat ==>> ", total_invoice_value)
                print("total_return_value vat  ==>> ", total_return_value)
                print("total_amount ==>> ", total_amount)

                previous_amount = rebate.prevous_amount

                progressive_percent = 0

                for progressive in rebate.progressive_ids:

                    if progressive.slab_type == 'fixed' and total_amount >=  progressive.slab_vale:
                        progressive_percent = progressive.rebate_percentage

                    if progressive.slab_type == 'percentage':
                        slab_amount = previous_amount + (previous_amount * progressive.percentage/100)
                        if total_amount >= slab_amount:
                            progressive_percent = progressive.rebate_percentage

                print("progressive_percent ==>> ", progressive_percent)

                if progressive_percent > 0.001:
                    progressive_rebate_amount = total_amount * (progressive_percent/100)
                    narration = 'Progressive Rebate : ' + rebate.name + ' : ' + \
                                str(progressive_percent) + ' of ' + str(total_amount)
                    self.create_accounting_entry(progressive_rebate_amount, rebate, narration)



    def create_accounting_entry(self, progressive_rebate_amount, rebate, narration):

        journal_id = self.env['ir.config_parameter'].sudo().get_param('kg_sarya_rebate.rebate_journal_id')
        provision_acc = self.env['ir.config_parameter'].sudo().get_param('kg_sarya_rebate.rebate_provision_account_id')
        if not journal_id or not provision_acc:
            _logger.warning("Scheduled action for rebate progressive entry is failed. "
                                "Please configure Rebate Journal and Rebate Provision account in settings")

        move_line_vals = []


        move_line_vals.append((0, 0, {
            'name': narration,
            'account_id': int(provision_acc),
            'debit': progressive_rebate_amount,
            'partner_id': rebate.rebate_customer_for_posting.id,
        }))
        move_line_vals.append((0, 0, {
            'name': narration,
            'account_id': rebate.rebate_customer_for_posting.property_account_receivable_id.id,
            'credit': progressive_rebate_amount,
            'partner_id': rebate.rebate_customer_for_posting.id,
        }))


        move_vals = {
            'ref': 'Progressive Rebate Entry: %s' % rebate.name,
            'journal_id': int(journal_id),
            'date': self.move_date,
            'rebate_type': 'progressive',
            'rebate_master_id': rebate.id,
            'line_ids': move_line_vals,
        }
        move = self.env['account.move'].create(move_vals)
        move.action_post()


    def get_invoice_value(self, rebate, price_list, partner_list):

        params = [price_list.id, self.from_date, self.to_date, tuple(partner_list), self.from_date, self.to_date]
        query = '''select mv.id from account_move as mv
                    JOIN sale_order as so ON mv.sale_order_id = so.id
                    where mv.state = 'posted'
                    AND mv.move_type = 'out_invoice'
                    AND mv.sale_order_id IS NOT NULL
                    AND so.pricelist_id = %s
                    AND mv.invoice_date >= %s
                    AND mv.invoice_date <= %s
                    UNION

                    select mv.id from account_move as mv
                    where mv.state = 'posted'
                    AND mv.move_type = 'out_invoice'
                    AND mv.sale_order_id IS NULL
                    AND mv.partner_id in %s
                    AND mv.invoice_date >= %s
                    AND mv.invoice_date <= %s'''
        self.env.cr.execute(query, tuple(params))

        move_ids = [x[0] for x in self.env.cr.fetchall()]

        if move_ids:

            # finding amount
            brand = rebate.brand_id.ids
            section = rebate.customer_section_ids.ids
            params = [self.from_date, self.to_date, tuple(move_ids)]
            query = '''SELECT SUM(mvl.product_packaging_qty*mvl.pkg_unit_price) as total_amount
                                            FROM account_move_line as mvl
                                            JOIN account_move as mv ON mvl.move_id = mv.id
                                            JOIN product_product as prd ON mvl.product_id = prd.id
                                            JOIN product_template as prd_t on prd.product_tmpl_id = prd_t.id
                                            WHERE mvl.product_id IS NOT NULL 
                                            AND mvl.exclude_from_invoice_tab IS False
                                            AND mvl.product_packaging_qty > 0.01 
                                            AND mvl.price_unit > 0.01 
                                            AND mvl.date >= %s
                                            AND mvl.date <= %s
                                            AND mv.id in %s'''

            if brand:
                params.append(tuple(brand))
                query = query + ' AND prd_t.brand in %s'
            if section:
                params.append(tuple(section))
                query = query + ' AND prd_t.section in %s'

            self.env.cr.execute(query, tuple(params))
            result = self.env.cr.fetchall()
            if result:
                return result[0][0]
            else:
                return 0
        else:
            return 0

    def get_credit_note_value(self, rebate, price_list, partner_list):

        params = [price_list.id, self.from_date, self.to_date, tuple(partner_list), self.from_date, self.to_date]
        #print("partner_list ==>> ", partner_list)
        query = '''select mv.id from account_move as mv
                    JOIN sale_order as so ON mv.sale_order_id = so.id
                    where mv.state = 'posted'
                    AND mv.move_type = 'out_refund'
                    AND mv.sale_order_id IS NOT NULL
                    AND so.pricelist_id = %s
                    AND mv.invoice_date >= %s
                    AND mv.invoice_date <= %s
                    UNION
                    select mv.id from account_move as mv
                    where mv.state = 'posted'
                    AND mv.move_type = 'out_refund'
                    AND mv.sale_order_id IS NULL
                    AND mv.partner_id in %s
                    AND mv.invoice_date >= %s
                    AND mv.invoice_date <= %s'''
        self.env.cr.execute(query, tuple(params))

        move_ids = [x[0] for x in self.env.cr.fetchall()]



        if move_ids:

            # finding amount
            brand = rebate.brand_id.ids
            section = rebate.customer_section_ids.ids
            params = [self.from_date, self.to_date, tuple(move_ids)]
            query = '''SELECT SUM(mvl.product_packaging_qty*mvl.pkg_unit_price) as total_amount
                                            FROM account_move_line as mvl
                                            JOIN account_move as mv ON mvl.move_id = mv.id
                                            JOIN product_product as prd ON mvl.product_id = prd.id
                                            JOIN product_template as prd_t on prd.product_tmpl_id = prd_t.id
                                            WHERE mvl.product_id IS NOT NULL 
                                            AND mvl.exclude_from_invoice_tab IS False
                                            AND mvl.product_packaging_qty > 0.01 
                                            AND mvl.price_unit > 0.01 
                                            AND mvl.date >= %s
                                            AND mvl.date <= %s
                                            AND mv.id in %s'''

            if brand:
                params.append(tuple(brand))
                query = query + ' AND prd_t.brand in %s'
            if section:
                params.append(tuple(section))
                query = query + ' AND prd_t.section in %s'

            self.env.cr.execute(query, tuple(params))
            result = self.env.cr.fetchall()
            if result:
                return result[0][0]
            else:
                return 0
        else:
            return 0




