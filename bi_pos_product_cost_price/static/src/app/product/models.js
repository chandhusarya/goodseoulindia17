/** @odoo-module */

import { Order, Orderline, Payment } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

// New orders are now associated with the current table, if any.
patch(Order.prototype, {
    setup(_defaultObj, options) {
        super.setup(...arguments);
        this.SearchCostPriceOrder = this.get_SearchCostPriceOrder() || 0;
    },
    //@override
    init_from_JSON(json){
        super.init_from_JSON(...arguments);
        this.SearchCostPriceOrder = json.SearchCostPriceOrder;
       
    },

    set_SearchCostPriceOrder(SearchCostPriceOrder){
        this.SearchCostPriceOrder = SearchCostPriceOrder;
    },
    get_SearchCostPriceOrder() {
        return this.SearchCostPriceOrder;
    },

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.SearchCostPriceOrder = this.SearchCostPriceOrder;
        return json
    },
    export_for_printing() {
        const json = super.export_for_printing(...arguments);
        json.SearchCostPriceOrder = this.get_SearchCostPriceOrder();
        return json;
    },
});