# -*- coding: utf-8 -*-
# Copyright (C) 2023 Konos and MercadoPago S.A.
# Licensed under the GPL-3.0 License or later.

{
    "name": "POS Redelcom",

    "summary": """
        Integrate your POS with a Redelcom payment terminal
    """,

    "author": "Konos Soluciones & Servicios",
    "website": "https://www.konos.cl",

    "category": "Sales/Point of Sale",
    "version": "17.0.0.1",

    "depends": [
        "point_of_sale",
    ],

    "data": [
        "security/ir.model.access.csv",
        "views/pos_payment_method_views.xml",
        "wizard/payment_status.xml",
    ],

    "assets": {
        "point_of_sale._assets_pos": [
            "pos_redelcom/static/**/*",
        ],
    },

    "installable": True,
    "license": "GPL-3",
}
