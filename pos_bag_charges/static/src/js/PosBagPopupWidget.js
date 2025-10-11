/** @odoo-module */

import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { Component } from "@odoo/owl";
import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { _t } from "@web/core/l10n/translation";
import { onMounted, useRef, useState } from "@odoo/owl";

export class PosBagPopup extends AbstractAwaitablePopup {
    static template = "pos_bag_charges.PosBagPopup";

    setup() {
        this.pos = usePos();
    }

    go_back_screen() {
                    this.showScreen('ProductScreen');
                    this.env.posbus.trigger('close-popup', {
                        popupId: this.props.id });
                }
    get bags() {
        let bags = [];
        $.each(this.props.products, function( i, prd ){
            prd['bag_image_url'] = `/web/image?model=product.product&field=image_128&id=${prd.id}&write_date=${prd.write_date}&unique=1`;
            bags.push(prd)
        });
        return bags;
    }
    
    click_on_bag_product(event) {
        var self = this;
        var bag_id = parseInt(event.currentTarget.dataset['productId'])
        
        // self.env.pos.get_order().add_product(self.env.pos.db.product_by_id[bag_id]);
        this.pos.addProductToCurrentOrder(this.pos.db.product_by_id[bag_id])
        this.pos.showScreen('ProductScreen');
        this.props.close({ confirmed: false, payload: false });
    }
}

ProductScreen.addControlButton({
    component: PosBagPopup,
    condition: function () {
        return this.pos.config.allow_bag_popup;
    },
});
