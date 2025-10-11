import ast

from odoo import models, fields, _
from odoo.exceptions import UserError


class SalesReturn(models.TransientModel):
    _name = 'sales.return.wizard'
    _description = 'Sales Return'

    partner_id = fields.Many2one('res.partner', 'Customer', required=True)
    invoice_id = fields.Many2one('account.move', 'Invoice', copy=False, tracking=True)

    picking_id = fields.Many2one('stock.picking', 'Delivery Order', copy=False, tracking=True)

    def action_process(self):
        return_type = self._context.get('return_type', 'invoice')
        if return_type == 'invoice':
            if not self.invoice_id:
                raise UserError(_("You must choose an invoice."))
            action = self.env["ir.actions.actions"]._for_xml_id("account.action_view_account_move_reversal")
            action['name'] = _('Credit Note')
            action['context'] = dict(ast.literal_eval(action.get('context')), active_ids=self.invoice_id.ids,
                                     active_model='account.move')
            return action
        if return_type == 'picking':
            if not self.picking_id:
                raise UserError(_("You must choose a delivery order."))
            action = self.env["ir.actions.actions"]._for_xml_id("stock.act_stock_return_picking")
            action['context'] = dict(ast.literal_eval(action.get('context')), active_ids=self.picking_id.ids,
                                     active_model='stock.picking')
            return action
