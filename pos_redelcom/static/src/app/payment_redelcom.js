/** @odoo-module */

/*
 * Copyright (C) 2023 Konos and MercadoPago S.A.
 * Licensed under the GPL-3.0 License or later.
 */

import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

export class PaymentRedelcom extends PaymentInterface {
    setup() {
        super.setup(...arguments);
    }
    async _redelcomFetchPaymentIntent (payment_method, pos_ref, name, amount) {
        try {
            let data = await this.env.services.orm.silent.call(
                "pos.payment.method",
                "redelcom_make_payment",
                [[payment_method.id], pos_ref, name, amount],
            );
            return data;
        } catch (error) {
            let message;
            if (error.code === 200) {
                message = error.data.message;
            } else {
                message = error.message;
            }
            this._showError(message);
            return false;
        };
    }
    async _redelcomMakePayment () {
        let line = this.pos.get_order().selected_paymentline;
        let payment_intent = await this._redelcomFetchPaymentIntent(
            line.payment_method, line.order.uid,
            line.order.name, line.amount);
        if (!payment_intent) {
            line.set_payment_status("retry");
            return false;
        }
        if (payment_intent.state == "RECHAZADO") {
            line.set_payment_status("retry");
            this._showError(payment_intent.message);
            return false;
        }
        line.transaction_id = payment_intent.transaction_id;
        line.card_type = payment_intent.card_type;
        line.set_payment_status("done");
        return true;
    }
    async send_payment_request (cid) {
        /**
         * Override
         */
        await super.send_payment_request(...arguments);
        const line = this.pos.get_order().selected_paymentline;
        line.set_payment_status("waiting");
        try {
            return await this._redelcomMakePayment();
        } catch (error) {
            this._showError(error);
            return false;
        }
    }
    async send_payment_cancel (order, cid) {
        super.send_payment_cancel(...arguments);
        return true;
    }
    _showError (msg, title) {
        if (!title) {
            title =  _t("Redelcom terminal error");
        }
        this.env.services.popup.add(ErrorPopup, {
            title: title,
            body: msg,
        });
    }
}
