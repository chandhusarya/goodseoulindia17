/** @odoo-module */

/*
 * Copyright (C) 2023 Konos and MercadoPago S.A.
 * Licensed under the GPL-3.0 License or later.
 */

import { register_payment_method } from "@point_of_sale/app/store/pos_store";
import { PaymentRedelcom } from "@pos_redelcom/app/payment_redelcom";

register_payment_method("redelcom", PaymentRedelcom);
