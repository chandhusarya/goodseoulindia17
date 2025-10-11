/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { Order, Orderline, Payment } from "@point_of_sale/app/store/models";

patch(OrderWidget.prototype, {
    setup() {
        super.setup();
        this.pos=usePos();
    },
    _selectLine(event) {
    
        if(event.order){
        
             this.env.services.pos.get_order().set_SearchCostPriceOrder(event.order.selected_orderline.product.standard_price);
        }
       
        
    },
});