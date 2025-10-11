# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.tools import float_is_zero, float_compare, convert


class PosSession(models.Model):
    _inherit = 'pos.session'

    account_analytic_id = fields.Many2one(
        comodel_name='account.analytic.account',
        related="config_id.analytic_account_id",
        store=True,
        string='Analytic Account',
        copy=False
    )
    def _create_account_move(self, balancing_account=False,
                             amount_to_balance=0,
                             bank_payment_method_diffs=None):
        """Call the parent class method using super() and creates
         analytic distribution model"""
        res = super()._create_account_move(balancing_account,
                                           amount_to_balance,
                                           bank_payment_method_diffs)
        self.account_analytic_id = self.config_id.analytic_account_id
        if self.account_analytic_id:
            for move in self._get_related_account_moves():
                for rec in move.line_ids:
                    rec.write({
                        'analytic_distribution': {
                            self.config_id.analytic_account_id.id: 100
                        }
                    })
        else:
            for move in self._get_related_account_moves():
                for rec in move.line_ids:
                    rec.write({
                        'analytic_distribution': {}
                    })
        return res
