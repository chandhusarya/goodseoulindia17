# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round
from odoo import api, fields, models, _

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    parent_production_id = fields.Many2one('mrp.production', string='Parent MO', readonly=True, copy=False)
    root_production_id = fields.Many2one('mrp.production', string='Root MO', readonly=True, copy=False)
    related_production_ids = fields.One2many('mrp.production', 'root_production_id', string='Related Productions')
    actual_qty = fields.Float(string='Actual Quantity')
    do_not_update_production_chain = fields.Boolean("Do Not Update Production Chain", default=False)

    starting_production_id = fields.Many2one('mrp.production', string='Starting Production', readonly=True, copy=False)
    production_level = fields.Integer("Level", default=1)
    auto_cost_corrected = fields.Boolean("Auto Cost Corrected", default=False, copy=False)


    def button_mark_done(self):
        res =  super(MrpProduction, self).button_mark_done()
        for order in self:
            if order.state == 'done':
                order.correct_final_product_cost_final_check()
        return res


    def correct_final_product_cost_final_check(self):

        for mo in self:
            total_cost = 0.0
            for raw in mo.move_raw_ids:
                for valuation in raw.stock_valuation_layer_ids:
                    total_cost += valuation.value

            total_cost = (total_cost * -1)
            unit_final_cost = total_cost/mo.qty_producing
            unit_final_cost += mo.extra_cost

            account_wise_cost_mapping = {}
            credit_value = unit_final_cost
            if mo.extra_cost > 0:
                for cost_lines in mo.bom_id.cost_lines:
                    account_wise_cost_mapping[cost_lines.account_id.id] = cost_lines.extra_cost
                    credit_value -= cost_lines.extra_cost

            for finished_move in mo.move_finished_ids:
                for valuation in finished_move.stock_valuation_layer_ids:

                    if valuation.unit_cost == unit_final_cost:
                        continue

                    valuation.auto_cost_corrected = True

                    valuation.write({'unit_cost': unit_final_cost, 'value': unit_final_cost * valuation.quantity})
                    if valuation.remaining_qty > 0:
                        valuation.write({'remaining_value': unit_final_cost * valuation.remaining_qty})

                    account_move_id = valuation.account_move_id
                    for move_line in account_move_id.line_ids:
                        if move_line.account_id.name == 'INVENTORY ON HAND':
                            final_cost_value = unit_final_cost * valuation.quantity
                            self.env.cr.execute("""
                                 UPDATE account_move_line
                                 SET debit = %s,
                                     credit = 0
                                 WHERE id = %s
                             """, (final_cost_value, move_line.id))
                        elif move_line.account_id.id in account_wise_cost_mapping:
                            credit_mapping_value = account_wise_cost_mapping[move_line.account_id.id] * valuation.quantity
                            self.env.cr.execute("""
                                                             UPDATE account_move_line
                                                             SET debit = 0,
                                                                 credit = %s,
                                                                 amount_residual = %s
                                                             WHERE id = %s
                                                         """, (credit_mapping_value, credit_mapping_value * -1, move_line.id))

                        else:
                            final_credit_value = credit_value * valuation.quantity
                            self.env.cr.execute("""
                                 UPDATE account_move_line
                                 SET debit = 0,
                                     credit = %s,
                                     amount_residual = %s
                                 WHERE id = %s
                             """, (final_credit_value, final_credit_value*-1, move_line.id))

                    valuation.correct_cost()




    def check_all_production_cost(self):

        all_starting_productions = self.env['mrp.production'].search([('state', '=', 'done'), ('date_finished', '>', '2025-03-31 23:59:59')],  order = 'id desc')

        all_starting_productions.correct_final_product_cost()



    def correct_final_product_cost(self):

        for mo in self:

            print("mo id ==================>> ", mo.id)

            total_cost = 0.0
            for raw in mo.move_raw_ids:
                for valuation in raw.stock_valuation_layer_ids:
                    total_cost += valuation.value


            total_cost = (total_cost * -1)
            unit_final_cost = total_cost/mo.qty_producing
            unit_final_cost += mo.extra_cost


            account_wise_cost_mapping = {}
            credit_value = unit_final_cost
            if mo.extra_cost > 0:
                for cost_lines in mo.bom_id.cost_lines:
                    account_wise_cost_mapping[cost_lines.account_id.id] = cost_lines.extra_cost
                    credit_value -= cost_lines.extra_cost

            for finished_move in mo.move_finished_ids:
                for valuation in finished_move.stock_valuation_layer_ids:
                    valuation.write({'unit_cost': unit_final_cost, 'value': unit_final_cost * valuation.quantity})
                    if valuation.remaining_qty > 0:
                        valuation.write({'remaining_value': unit_final_cost * valuation.remaining_qty})

                    account_move_id = valuation.account_move_id
                    for move_line in account_move_id.line_ids:
                        if move_line.account_id.name == 'INVENTORY ON HAND':
                            final_cost_value = unit_final_cost * valuation.quantity
                            self.env.cr.execute("""
                                 UPDATE account_move_line
                                 SET debit = %s,
                                     credit = 0
                                 WHERE id = %s
                             """, (final_cost_value, move_line.id))
                        elif move_line.account_id.id in account_wise_cost_mapping:
                            credit_mapping_value = account_wise_cost_mapping[move_line.account_id.id] * valuation.quantity
                            self.env.cr.execute("""
                                                             UPDATE account_move_line
                                                             SET debit = 0,
                                                                 credit = %s,
                                                                 amount_residual = %s
                                                             WHERE id = %s
                                                         """, (credit_mapping_value, credit_mapping_value * -1, move_line.id))

                        else:
                            final_credit_value = credit_value * valuation.quantity
                            self.env.cr.execute("""
                                 UPDATE account_move_line
                                 SET debit = 0,
                                     credit = %s,
                                     amount_residual = %s
                                 WHERE id = %s
                             """, (final_credit_value, final_credit_value*-1, move_line.id))

                    valuation.correct_cost()



    def action_confirm(self):
        for mo in self:

            mo.extra_cost = mo.bom_id.extra_cost
        return super(MrpProduction, self).action_confirm()

    def _cal_price(self, consumed_moves):
        work_center_cost = 0

        finished_move = self.move_finished_ids.filtered(
            lambda x: x.product_id == self.product_id and x.state not in ('done', 'cancel') and x.quantity > 0)
        if finished_move:
            finished_move.ensure_one()

            print("finished_move ======>> ", finished_move)

            for work_order in self.workorder_ids:
                work_center_cost += work_order._cal_cost()
            quantity = finished_move.product_uom._compute_quantity(
                finished_move.quantity, finished_move.product_id.uom_id)
            extra_cost = self.extra_cost * quantity

            print("work_center_cost ======>> ", work_center_cost)
            print("quantity         ======>> ", quantity)
            print("extra_cost       ======>> ", extra_cost)

            #We need only over head costs, Not material cost
            total_cost =  work_center_cost + extra_cost

            print("total_cost       ======>> ", total_cost)



            byproduct_moves = self.move_byproduct_ids.filtered(
                lambda m: m.state not in ('done', 'cancel') and m.quantity > 0)
            byproduct_cost_share = 0
            for byproduct in byproduct_moves:


                if byproduct.cost_share == 0:
                    continue
                byproduct_cost_share += byproduct.cost_share
                if byproduct.product_id.cost_method in ('fifo', 'average'):
                    byproduct_cost = total_cost * byproduct.cost_share / 100 / byproduct.product_uom._compute_quantity(
                        byproduct.quantity, byproduct.product_id.uom_id)
                    byproduct.is_production_move = True
                    byproduct.overhead_production_cost = byproduct_cost
                    byproduct.bom_id = self.bom_id.id
                    byproduct.production_id = self.id


            if finished_move.product_id.cost_method in ('fifo', 'average'):
                finished_move_cost = total_cost * float_round(1 - byproduct_cost_share / 100,
                                                                    precision_rounding=0.0001) / quantity
                finished_move.is_production_move = True
                finished_move.overhead_production_cost = finished_move_cost
                finished_move.bom_id = self.bom_id.id
                finished_move.production_id = self.id
        #Calling Super class method to calculate price
        res = super(MrpProduction, self)._cal_price(consumed_moves)
        return res


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['actual_qty'] = vals['product_qty']

        res = super().create(vals_list)
        for mo in res:
            get_sources = mo._get_sources()
            for source_mo in get_sources:
                if source_mo.starting_production_id:
                    mo.starting_production_id = source_mo.starting_production_id.id
                else:
                    mo.starting_production_id = source_mo.id

                mo.production_level = source_mo.production_level + 1 if source_mo.production_level else 1
        return res


    # For reporting
    def get_materials(self):
        processed_mos = set()
        intermediate_dict = {}
        storable_list = []
        consumable_list = []

        def collect_all_mos(mo):
            if mo.id in processed_mos:
                return
            processed_mos.add(mo.id)

            status = dict(self.env['mrp.production'].fields_get(['state'])['state']['selection']).get(mo.state, '')

            # Record intermediate product
            product = mo.product_id
            packaging = product.packaging_ids.filtered(lambda p: p.primary_unit)[:1] or False
            intermediate_dict[product.id] = {
                'product': product,
                'qty': mo.product_qty,
                'available': product.qty_available,
                'uom': mo.product_uom_id,
                'mo': mo,
                'status': status,
                'packaging': packaging
            }

            # Raw material lines (excluding intermediate products)
            for move in mo.move_raw_ids.filtered(lambda m: m.product_id.type in ['product', 'consu']):
                p = move.product_id
                if p.id in intermediate_dict:
                    continue  # already captured as intermediate

                line = {
                    'product': p,
                    'qty': move.product_uom_qty,
                    'available': p.qty_available,
                    'uom': move.product_uom,
                    'mo': mo,
                    'status': status,
                    'packaging': p.packaging_ids.filtered(lambda pk: pk.primary_unit)[:1] or False
                }

                if p.type == 'product':
                    storable_list.append(line)
                elif p.type == 'consu':
                    consumable_list.append(line)

            # Recursively collect child MOs
            child_mos = self.search([('origin', '=', mo.name)])
            for child in child_mos:
                collect_all_mos(child)

        for mo in self:
            collect_all_mos(mo)

        # Remove any intermediates that accidentally got included
        storable_list = [s for s in storable_list if s['product'].id not in intermediate_dict]
        consumable_list = [c for c in consumable_list if c['product'].id not in intermediate_dict]

        # Sort by MO name descending
        storable_list.sort(key=lambda x: x['mo'].name, reverse=True)
        consumable_list.sort(key=lambda x: x['mo'].name, reverse=True)

        return {
            'intermediate': intermediate_dict,
            'storable': storable_list,
            'consumable': consumable_list,
        }

    def _split_moves_by_move_line(self):
        context = dict(self.env.context, do_not_unreserve=True, do_not_propagate=True, mail_notrack=True,
                       tracking_disable=True)
        all_moves = self.move_raw_ids | self.move_finished_ids
        for move in all_moves.with_context(tracking_disable=True):
            if move.product_id.cost_level == 'lot' and len(
                    move.move_line_ids) > 1 and move.product_id.type == 'product':
                line1_initial_demand = move.product_uom_qty
                for move_line in move.move_line_ids[1:]:
                    if move_line.quantity:
                        new_move = move.with_context(context).copy(default={
                            'product_uom_qty': move_line.quantity,
                            'move_orig_ids': [(6, 0, move.move_orig_ids.ids)],
                            'move_dest_ids': [(6, 0, move.move_dest_ids.ids)],
                            'raw_material_production_id': move.raw_material_production_id.id,
                            'production_id': move.production_id.id,
                            'picking_type_id': move.picking_type_id.id,
                        })
                        move_line.with_context(context).write({
                            'move_id': new_move.id,
                            'quantity': move_line.quantity
                        })
                        new_move.with_context(context)._action_confirm(merge=False)

                        print("new_move =========>> ", new_move)

                        line1_initial_demand -= new_move.product_uom_qty
                    else:
                        move_line.with_context(context).write({'move_id': None, 'picking_id': None, 'state': 'draft'})
                move.with_context(context).write({'product_uom_qty': line1_initial_demand})

    def button_mark_done(self):
        self._split_moves_by_move_line()
        res = super(MrpProduction, self).button_mark_done()
        if not self.do_not_update_production_chain:
            self.update_production_qty()
        return res




    def update_production_qty(self):
        if self.qty_producing != self.product_qty:
            produced_qty = self.qty_producing
            to_update_child = self._update_production_qty_recursive(produced_qty, self)
            if to_update_child:
                fist_mo = min(to_update_child)
                fist_mo = self.env['mrp.production'].browse(fist_mo)
                already_updated = [self.id] + to_update_child
                fist_mo._update_child_production_qty(already_updated)




    def _update_production_qty_recursive(self, produced_qty, triggered_mo):

        to_update_child = []
        get_sources = self._get_sources()
        for source_mo in get_sources:
            # Update the production quantity recursively
            if source_mo.state not in ['done', 'cancel']:
                to_update_child.append(source_mo.id)
                bom = source_mo.bom_id
                source_bom_qty = source_mo.product_qty
                do_source_qty_updated = False

                for bom_item in bom.bom_line_ids:
                    if bom_item.product_id.id == self.product_id.id:

                        max_possible = produced_qty / bom_item.product_qty
                        new_source_product_qty = bom.product_qty * max_possible

                        qty_producing_before_updation = source_mo.qty_producing
                        source_mo.qty_producing = new_source_product_qty
                        source_mo._onchange_producing()
                        note_subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note')
                        source_mo.message_post(
                            body=_(
                                'Production quantity updated from %s to %s  based on Chlid MO %s production confirmation' % (
                                    str(qty_producing_before_updation), str(new_source_product_qty), triggered_mo.name)
                                ),
                            message_type='comment',
                            subtype_id=note_subtype_id
                        )
                        to_update_child_recursive = source_mo._update_production_qty_recursive(new_source_product_qty, triggered_mo)
                        if to_update_child_recursive:
                            to_update_child.extend(to_update_child_recursive)

        return to_update_child




    def _update_child_production_qty(self, already_updated):
        children_mos = self._get_children()
        children_updated = []
        for child_mo in children_mos:
            if child_mo.id not in already_updated and child_mo.state not in ['done', 'cancel']:
                for mo_line in self.move_raw_ids:
                    if mo_line.product_id.id == child_mo.product_id.id:
                        child_mo.qty_producing = mo_line.should_consume_qty
                        child_mo._onchange_producing()
                children_updated.append(child_mo.id)
                already_updated.append(child_mo.id)
            childs_children_updated = child_mo._update_child_production_qty(already_updated)
            if childs_children_updated:
                children_updated.extend(childs_children_updated)
        return children_updated




    def open_related_production(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Child Production',
            'res_model': 'mrp.production',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }

    # def button_mark_done(self):
    #     print("<><><><><><><><><><>")
    #     print(self.qty_producing, self.actual_qty)
    #     if self.qty_producing != self.actual_qty:
    #         mo_id = self.parent_production_id
    #         if self.qty_producing != self.product_qty:
    #             raise UserError("Mismatch in Planned quantity(%d) and actual produced(%d), update the planned quantity and produce again."%(self.qty_producing,self.product_qty))
    #         while mo_id:
    #             print("MO", mo_id)
    #             new_qty = (mo_id.product_qty / self.actual_qty) * self.qty_producing
    #             print("mo_id.product_qty", mo_id.product_qty)
    #             print("self.qty_producing", self.qty_producing)
    #             print("self.product_qty", self.product_qty)
    #             print("new_qty", new_qty)
    #             qty_chg_wizard = self.env['change.production.qty'].create({'mo_id': mo_id.id, 'product_qty': new_qty})
    #             qty_chg_wizard.change_prod_qty()
    #             # self.env['change.production.qty'].with_context({'mo_id': mo_id.id, 'product_qty': new_qty}).change_prod_qty()
    #             mo_id = mo_id.parent_production_id or False
    #             print("===================+++++++++++++++++++++")
    #             print("mo_id.parent_production_id", mo_id and mo_id.parent_production_id)
    #             print('mo_id', mo_id)
    #     return super(MrpProduction, self).button_mark_done()

class MrpBomCost(models.Model):
    _name = 'mrp.bom.cost'

    bom_id = fields.Many2one(comodel_name='mrp.bom', string='Bom')
    account_id = fields.Many2one(comodel_name='account.account', string='Account')
    extra_cost = fields.Float(copy=False, string='Over head Cost')
    description = fields.Char(string='Description')



class MRPBom(models.Model):
    _inherit = 'mrp.bom'

    bom_item_id = fields.Many2one(comodel_name='mrp.bom.item', string='Bom Item')
    bom_item_parent_id = fields.Many2one(comodel_name='mrp.bom.item', string='Bom Item Parent')
    cost_lines = fields.One2many('mrp.bom.cost', 'bom_id', string='Cost Lines')
    extra_cost = fields.Float(string='Extra Unit Cost', compute='_compute_extra_cost')

    def _compute_extra_cost(self):
        for bom in self:
            extra_cost = 0.0
            for cost_line in bom.cost_lines:
                extra_cost += cost_line.extra_cost
            bom.extra_cost = extra_cost



    @api.onchange('bom_item_id')
    def onchange_bom_item_id(self):
        if self.bom_item_id:
            self.bom_item_parent_id = self.bom_item_id.parent_id and self.bom_item_id.parent_id.id or False





