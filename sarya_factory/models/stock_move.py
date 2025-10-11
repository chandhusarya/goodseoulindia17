
from odoo import models, fields, _, api
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = 'stock.move'

    is_production_move = fields.Boolean(string='Is Production', default=False)
    overhead_production_cost = fields.Float("Overhead Production Cost", default=0.0)
    bom_id = fields.Many2one('mrp.bom', string='BOM')
    production_id = fields.Many2one('mrp.production', string='Production Order')


    def _account_entry_move(self, qty, description, svl_id, cost):
        res = super(StockMove, self)._account_entry_move(qty, description, svl_id, cost)

        stock_valuation = self.env['stock.valuation.layer'].browse(svl_id)
        stock_move_id = stock_valuation.stock_move_id
        if stock_move_id.is_production_move and stock_move_id.production_id and stock_move_id.overhead_production_cost > 0.001:
            for move in res:
                new_line = []
                for move_line in move['line_ids']:
                    if move_line[2].get('balance', 0) < -0.01 and move_line[2].get('quantity', 0) > 0.01:

                        balance = move_line[2].get('balance', 0) * -1

                        print("\n\n\n\nbalance =======>> ", balance)

                        print("stock_move_id.overhead_production_cost ====>> ", stock_move_id.overhead_production_cost)

                        total_overhead_value = stock_move_id.overhead_production_cost * move_line[2].get('quantity', 0)
                        new_balance = balance - total_overhead_value
                        move_line[2]['balance'] = new_balance * -1

                        print("new_balance =======>> ", new_balance)

                        overhead_account_param = "manufacturing_overhead_%s" % stock_move_id.company_id.id
                        overhead_account_head = self.env['ir.config_parameter'].sudo().get_param(overhead_account_param, False)
                        if not overhead_account_head:
                            raise UserError(_("Please manufacturing over head account for company %s in formate %s" % (stock_move_id.company_id.name, overhead_account_param)))
                        overhead_account_head = int(overhead_account_head)



                        print("total_overhead_value =======>> ", total_overhead_value)

                        bom = stock_move_id.bom_id
                        ratio = stock_move_id.overhead_production_cost/bom.extra_cost
                        print("ratio =======>> ", ratio)
                        total_overhead = 0
                        for cost in bom.cost_lines:

                            each_over_head = cost.extra_cost * ratio

                            print("each_over_head =======>> ", each_over_head)
                            each_total_overhead = each_over_head * move_line[2].get('quantity', 0)
                            total_overhead += each_total_overhead

                            print("each_total_overhead =======>> ", each_total_overhead)


                            new_line.append((0, 0, {
                                'name': move_line[2].get('name', '') + ' : ' + cost.description,
                                'product_id': move_line[2].get('product_id', False),
                                'quantity': move_line[2].get('quantity', 0),
                                'product_uom_id': move_line[2].get('product_uom_id', False),
                                'ref': move_line[2].get('ref', ''),
                                'partner_id': move_line[2].get('partner_id', False),
                                'balance': each_total_overhead * -1,
                                'account_id': cost.account_id.id,
                            }))

                        print("total_overhead =======>> ", total_overhead)
                        print("new_balance + total_overhead =======>> ", new_balance + total_overhead)

                    else:
                        print("\n\n\n\nmove_line[2].get('balance', 0) =======>> ", move_line[2].get('balance', 0))









                for each_line in new_line:
                    move['line_ids'].append(each_line)


        return res