/** @odoo-module */

import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { PosBagPopup } from "@pos_bag_charges/js/PosBagPopupWidget";

export class PosBagButton extends Component {
    static template = "pos_bag_charges.PosBagButton";

    setup() {
        this.pos = usePos();
        this.popup = useService("popup");
    }
    
    async onClick() {
        let self = this;
        let selectedOrder = self.pos.get_order();
        let category = self.env.services.pos.config.pos_bag_category_id;
        if(category){
            let products = self.env.services.pos.db.get_product_by_category(category[0]);
            if (products.length == 1) { 
                selectedOrder.add_product(products[0]);
                self.env.services.pos.set_order(selectedOrder);
                this.pos.showScreen('ProductScreen');
            }else{
                products.forEach(function(prd) {
                    prd['image_url'] = window.location.origin + '/web/binary/image?model=product.product&field=image_medium&id=' + prd.id;
                });
                self.popup.add(PosBagPopup, {'products': products});
            }   
        }
    }

}

ProductScreen.addControlButton({
    component: PosBagButton,
    position: ["before", "SetFiscalPositionButton"],
    condition: function () {
        return this.pos.config.allow_bag_charges;
    },
});


    