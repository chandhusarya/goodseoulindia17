# -*- coding: utf-8 -*-
# Copyright (C) 2023 Konos and MercadoPago S.A.
# Licensed under the GPL-3.0 License or later.

import logging
import time
import hmac
import base64
import json
import hashlib

import requests

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


MAX_RETRIES = 40
MIN_SALE = 50.0
TIMEOUT = 10

BASE_URL = {
    "live": "https://api.redelcom.cl:20010",
    "demo": "https://api-dev.redelcom.cl:20010",
}


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    redelcom_mode = fields.Selection([
        ("live", "Live"),
        ("demo", "Demo")],
        default="demo", copy=False,
        help="Environment in which transactions are executed.")
    redelcom_client = fields.Integer(
        copy=False,
        help="Client identifier in the Redelcom system.")
    redelcom_secret = fields.Char(
        copy=False,
        help="Secret key assigned to the client.")
    redelcom_terminal_serial = fields.Char(
        copy=False,
        help="10-digit number located on the back of the terminal.")
    redelcom_terminal_code = fields.Char(
        copy=False,
        help="Unique identifier associated with the terminal.")

    def _get_payment_terminal_selection(self):
        """
        Enables 'Redelcom' as a payment terminal for payment methods.

        :return: Payment terminals available.
        :rtype: list
        """
        res = super()._get_payment_terminal_selection()
        res.append(["redelcom", "Redelcom"])
        return res

    def _redelcom_authentication_token(self, endpoint, data):
        """
        Generates the authentication token for Redelcom API requests.

        :param endpoint: URL for which you want to make the request (str).
        :param data: Data to be included as part of the request (dict).

        :return: A string representing the authentication token.
        :rtype: str

        :raises UserError: If there is an error generating the token.
        """
        try:
            message = f"{endpoint},{data}"
            hmac_object = hmac.new(
                bytes(self.redelcom_secret, "utf-8"),
                msg=bytes(message, "utf-8"),
                digestmod=hashlib.sha256).digest()
            hmac_encode = base64.b64encode(hmac_object)
            token = f"{self.redelcom_client};{hmac_encode.decode('UTF-8')}"
        except Exception as error:
            _logger.exception("_redelcom_authentication_token: %s", error)
            raise UserError(_("Unable to generate authentication token"))
        return token

    @api.model
    def _redelcom_get_terminal_code(self, serial, mode):
        """
        Retrieves the unique identifier associated with the terminal.

        :param serial: The serial number of the terminal (str).
        :param mode: The mode of API request (str).

        :return: The response object containing the terminal identifier.
        :rtype: requests.models.Response

        :raises UserError: If there is an error retrieving the identifier.
        """
        try:
            endpoint = f"/v2/terminal?serialNumber={serial}"
            headers = {
                "X-Authentication":
                    self._redelcom_authentication_token(endpoint, "")
            }
            url = "".join([BASE_URL.get(mode), endpoint])
            response = requests.get(url, headers=headers, timeout=TIMEOUT)
            response.raise_for_status()
        except requests.exceptions.RequestException as error:
            _logger.exception("_redelcom_get_terminal_code: %s", error)
            raise UserError(_("Unable to retrieve the terminal code"))
        return response

    def _redelcom_create_payment_intent(self, pos_ref, name, amount):
        """
        Creates a payment intent in Redelcom.

        :param pos_ref: The reference of the point of sale transaction (str).
        :param name: The name or description of the payment (str).
        :param amount: The amount of the payment (int).

        :return: The response object containing the payment intent.
        :rtype: requests.models.Response

        :raises UserError: If there is an error creating the payment intent.
        """
        try:
            endpoint = "/v2/pago"
            payload = json.dumps({
                "userTransactionId": pos_ref,
                "description": name,
                "amount": amount,
                "terminalId": self.redelcom_terminal_code,
                # Although you can pay with card, cash or wallet, we
                # will always use card by default.
                "paymentType": "TARJETA",
            })
            headers = {
                "X-Authentication":
                    self._redelcom_authentication_token(endpoint, payload),
                "Content-Type": "application/json"
            }
            url = "".join([BASE_URL.get(self.redelcom_mode), endpoint])
            response = requests.post(
                url, headers=headers, data=payload, timeout=TIMEOUT)
            response.raise_for_status()
        except requests.exceptions.RequestException as error:
            _logger.exception("_redelcom_create_payment_intent: %s", error)
            raise UserError(_("Unable to create payment intent"))
        return response

    def _redelcom_get_payment_status(self, transaction_id):
        """
        Retrieves the payment status of the transaction from Redelcom.

        :param transaction_id: ID used to identify the payment (str).

        :return: The response object containing the payment status.
        :rtype: requests.models.Response

        :raises UserError: If there is an error retrieving the payment status.
        """
        try:
            endpoint = f"/v2/pago?rdcTransactionId={transaction_id}"
            headers = {
                "X-Authentication":
                    self._redelcom_authentication_token(endpoint, "")
            }
            url = "".join([BASE_URL.get(self.redelcom_mode), endpoint])
            response = requests.get(url, headers=headers, timeout=TIMEOUT)
            response.raise_for_status()
        except requests.exceptions.RequestException as error:
            _logger.exception("_redelcom_get_payment_status: %s", error)
            raise UserError(_("Unable to retrieve payment status"))
        return response

    def redelcom_make_payment(self, pos_ref, name, amount):
        """
        Initiates a payment transaction through Redelcom API.

        :param pos_ref: The reference of the point of sale transaction (str).
        :param name: The name or description of the payment (str).
        :param amount: The amount of the payment (int).

        :return: Details of the transaction.
        :rtype: dict

        :raises ValidationError: If there are validation errors preventing
            the payment.
        :raises UserError: If the transaction cannot be completed within
            the maximum retries.
        """
        conditions = {
            _("The terminal code is not defined"):
            not self.redelcom_terminal_code,
            _("The sale amount does not reach the minimum required"):
            amount <= MIN_SALE,
        }
        messages = [key for key, value in conditions.items() if value]
        if messages:
            raise ValidationError(_(
                "Cannot continue due to the following:\n%s") %
                    ("\n".join(messages)))
        _logger.info("Creating payment intention")
        intent_request = self._redelcom_create_payment_intent(
            pos_ref, name, amount)
        intent = intent_request.json()
        transaction_id = intent.get("rdcTransactionId")
        data = {}
        retries = MAX_RETRIES
        # We keep making requests until we get a response or reach
        # the maximum number of retries. In the worst case we wait
        # 160 seconds before aborting the transaction
        _logger.info("Getting payment status")
        while retries > 0:
            _logger.info("Remaining attempts: %s", retries)
            time.sleep(4)
            payment_request = self._redelcom_get_payment_status(
                transaction_id)
            if payment_request.status_code == 204:
                retries -= 1
                continue
            payment = payment_request.json()
            if payment.get("ESTADO") in ["APROBADO", "RECHAZADO"]:
                data.update({
                    "state": payment.get("ESTADO"),
                    "message": payment.get("MENSAJE_VISOR"),
                    "transaction_id": transaction_id,
                    "card_type": payment.get("MEDIO_PAGO"),
                })
                break
            retries -= 1
        if not data:
            raise UserError(_(
                "Transaction %s could not be completed") % transaction_id)
        return data

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            terminal = record.use_payment_terminal
            if terminal and terminal == "redelcom":
                code_request = record._redelcom_get_terminal_code(
                    record.redelcom_terminal_serial,
                    record.redelcom_mode)
                code = code_request.json()
                record.write({
                    "redelcom_terminal_code": code.get("terminal")})
        return records

    def write(self, vals):
        if "redelcom_terminal_serial" in vals and\
                self.use_payment_terminal == "redelcom":
            serial = vals.get("redelcom_terminal_serial")
            mode = self.redelcom_mode
            code_request = self._redelcom_get_terminal_code(serial, mode)
            code = code_request.json()
            vals.update({
                "redelcom_terminal_code": code.get("terminal")})
        return super().write(vals)
