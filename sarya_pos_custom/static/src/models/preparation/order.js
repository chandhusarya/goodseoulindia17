/** @odoo-module **/

import { Component, useState, onWillUnmount, useRef } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { Order } from "@pos_preparation_display/app/components/order/order";
patch(Order.prototype, {

    setup() {
        super.setup(...arguments);
//        console.log('Inside preparation order custom.')
        this.interval = setInterval(() => {
            const timeDiff = this._computeDuration()
            this.state.duration = (Math.floor( timeDiff/ 60)).toString() + ":" + (timeDiff % 60).toString()
        }, 1000);

//        onWillUnmount(() => {
//            clearInterval(this.interval);
//        });

    },


    _computeDuration() {
        const timeDiff = this.props.order.computeDuration();

        if (Math.floor(timeDiff / 60) > this.stage.alertTimer) {
            this.isAlert = true;
        } else {
            this.isAlert = false;
        }

        return timeDiff;
    },

});