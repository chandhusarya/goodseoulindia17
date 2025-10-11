/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Order } from "@pos_preparation_display/app/models/order";
import { deserializeDateTime } from "@web/core/l10n/dates";

patch(Order.prototype, {
    computeDuration() {
//        console.log('Inside custom');
        const timeDiff = (
            (luxon.DateTime.now().ts - deserializeDateTime(this.lastStageChange).ts) /
            1000
        ).toFixed(0);
        return Math.round(timeDiff / 1);
    },
});