# Copyright (C) Softhealer Technologies.

from odoo import api, fields, models, Command, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError


class AccountMove(models.Model):
    _inherit = "account.move"

    pdc_payment_id = fields.Many2one('pdc.wizard', string="PDC Payment")


    # @api.depends(
    #     'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
    #     'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
    #     'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
    #     'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
    #     'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
    #     'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
    #
    #     'line_ids.matched_debit_ids.debit_move_id.move_id.pdc_payment_id.state',
    #     'line_ids.matched_credit_ids.credit_move_id.move_id.pdc_payment_id.state',
    #
    #     'line_ids.debit',
    #     'line_ids.credit',
    #     'line_ids.currency_id',
    #     'line_ids.amount_currency',
    #     'line_ids.amount_residual',
    #     'line_ids.amount_residual_currency',
    #     'line_ids.payment_id.state',
    #     'line_ids.full_reconcile_id')
    # def _compute_amount(self):
    #     data = super(AccountMove, self)._compute_amount()
    #
    #     for move in self:
    #         if move._payment_state_matters() and move.state == 'posted':
    #             reconciled_lines = move.line_ids.filtered( lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
    #             reconciled_amls = reconciled_lines.mapped('matched_debit_ids.debit_move_id') + \
    #                               reconciled_lines.mapped('matched_credit_ids.credit_move_id')
    #
    #             move_id = []
    #             for recon_aml in reconciled_amls:
    #                 move_id.append(recon_aml.move_id.id)
    #             if move_id:
    #                 #Check is this pdc entry
    #                 pdc = self.env['pdc.wizard'].search([('move_register_id', 'in', move_id)])
    #                 if pdc:
    #                     if pdc.state == 'cleared':
    #                         move.payment_state = 'paid'
    #                     elif pdc.state == 'registered':
    #                         move.payment_state = 'in_payment'
    #     return data
