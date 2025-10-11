from odoo import fields, models, api, _, SUPERUSER_ID
from odoo.tools import float_compare, OrderedSet
from collections import defaultdict
from datetime import datetime
from dateutil.relativedelta import relativedelta


class StockRule(models.Model):
    _inherit = 'stock.rule'


    @api.model
    def _run_manufacture(self, procurements):
        new_productions_values_by_company = defaultdict(list)
        for procurement, rule in procurements:
            if float_compare(procurement.product_qty, 0, precision_rounding=procurement.product_uom.rounding) <= 0:
                # If procurement contains negative quantity, don't create a MO that would be for a negative value.
                continue
            bom = rule._get_matching_bom(procurement.product_id, procurement.company_id, procurement.values)

            mo = self.env['mrp.production']
            mto_route = self.env['stock.warehouse']._find_global_route('stock.route_warehouse0_mto', _('Replenish on Order (MTO)'))
            if rule.route_id != mto_route and procurement.origin != 'MPS':
                gpo = rule.group_propagation_option
                group = (gpo == 'fixed' and rule.group_id) or \
                        (gpo == 'propagate' and 'group_id' in procurement.values and procurement.values['group_id']) or False
                domain = (
                    ('bom_id', '=', bom.id),
                    ('product_id', '=', procurement.product_id.id),
                    ('state', 'in', ['draft', 'confirmed']),
                    ('is_planned', '=', False),
                    ('picking_type_id', '=', rule.picking_type_id.id),
                    ('company_id', '=', procurement.company_id.id),
                    ('user_id', '=', False),
                )
                if procurement.values.get('orderpoint_id'):
                    procurement_date = datetime.combine(
                        fields.Date.to_date(procurement.values['date_planned']) - relativedelta(days=int(bom.produce_delay)),
                        datetime.max.time()
                    )
                    domain += ('|',
                               '&', ('state', '=', 'draft'), ('date_deadline', '<=', procurement_date),
                               '&', ('state', '=', 'confirmed'), ('date_start', '<=', procurement_date))
                if group:
                    domain += (('procurement_group_id', '=', group.id),)
                mo = self.env['mrp.production'].sudo().search(domain, limit=1)
            if not mo:
                new_productions_values_by_company[procurement.company_id.id].append(rule._prepare_mo_vals(*procurement, bom))
                print("new_productions_values_by_company", new_productions_values_by_company)
                # llll
            else:
                self.env['change.production.qty'].sudo().with_context(skip_activity=True).create({
                    'mo_id': mo.id,
                    'product_qty': mo.product_id.uom_id._compute_quantity((mo.product_uom_qty + procurement.product_qty), mo.product_uom_id)
                }).change_prod_qty()


        note_subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note')
        print("new_productions_values_by_company", new_productions_values_by_company)
        for company_id, productions_values in new_productions_values_by_company.items():
            # create the MO as SUPERUSER because the current user may not have the rights to do it (mto product launched by a sale for example)
            for productions_value in productions_values:
                if 'origin' in productions_value:
                    prod = self.env['mrp.production'].search([('name', '=', productions_value['origin'])])
                    productions_value['parent_production_id'] = prod and prod.id or False
                    productions_value['root_production_id'] = prod and prod.root_production_id and prod.root_production_id.id or prod.id or False
            print("productions_values", productions_values)
            # mmmmmmmmmm
            productions = self.env['mrp.production'].with_user(SUPERUSER_ID).sudo().with_company(company_id).create(productions_values)
            productions.filtered(self._should_auto_confirm_procurement_mo).action_confirm()

            for production in productions:
                origin_production = production.move_dest_ids and production.move_dest_ids[0].raw_material_production_id or False
                orderpoint = production.orderpoint_id
                if orderpoint and orderpoint.create_uid.id == SUPERUSER_ID and orderpoint.trigger == 'manual':
                    production.message_post(
                        body=_('This production order has been created from Replenishment Report.'),
                        message_type='comment',
                        subtype_id=note_subtype_id
                    )
                elif orderpoint:
                    production.message_post_with_source(
                        'mail.message_origin_link',
                        render_values={'self': production, 'origin': orderpoint},
                        subtype_id=note_subtype_id,
                    )
                elif origin_production:
                    production.message_post_with_source(
                        'mail.message_origin_link',
                        render_values={'self': production, 'origin': origin_production},
                        subtype_id=note_subtype_id,
                    )
        return True
