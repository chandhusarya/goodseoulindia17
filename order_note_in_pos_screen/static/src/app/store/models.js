/** @odoo-module */

import {Order} from "@point_of_sale/app/store/models";
import {patch} from "@web/core/utils/patch";
import {onMounted} from "@odoo/owl";
// An order more or less represents the content of a customer's shopping cart (the OrderLines)
// plus the associated payment information (the Paymentlines)
// there is always an active ('selected') order in the Pos, a new one is created
// automaticaly once an order is completed and sent to the server.

patch(Order.prototype, {
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.note = this.note
        return json;
    },

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.note = json.note;
    },

    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        result.note = this.note;
        return result;
    },

    set_order_note(note) {
        this.note = note || "";
    }
});
