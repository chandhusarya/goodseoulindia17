# -*- coding: utf-8 -*-
# Copyright (C) 2023 Konos and MercadoPago S.A.
# Licensed under the GPL-3.0 License or later.

from odoo import fields, models


class PaymentStatusWizard(models.TransientModel):
    _name = "payment.status.wizard"
    _description = "Payment status wizard"

    payment_method_id = fields.Many2one(
        "pos.payment.method", string="Payment Method",
        help="Payment method associated with a Redelcom terminal.")
    payment_status = fields.Char(
        default="unknown", help="Payment status in Redelcom.")
    transaction_number = fields.Char(
        help="Transaction number for which you want to obtain the status.")

    def get_payment_status(self):
        """
        Gets the payment status of a specific transaction.

        This method retrieves the payment status by calling the
        '_redelcom_get_payment_status' method of the associated
        payment method.

        :return: A ir.actions.act_window.
        :rtype: dict
        """
        payment_request =\
            self.payment_method_id._redelcom_get_payment_status(
                self.transaction_number)
        payment = payment_request.json()
        self.payment_status = payment.get("ESTADO")
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "res_id": self.id,
            "views": [(False, "form")],
            "target": "new",
        }
