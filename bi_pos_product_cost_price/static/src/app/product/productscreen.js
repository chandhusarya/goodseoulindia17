/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

import { _t } from "@web/core/l10n/translation";

patch(ProductScreen.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
        // this.ui = useState(useService("ui"));
        this.popup = useService("popup");
    },
    get currentOrder() {
        return this.pos.get_order();
    },

    async _addProduct(product, options) {
        this.currentOrder.add_product(product, options);
        this.currentOrder.set_SearchCostPriceOrder(product.standard_price);
    },


    async updateSelectedOrderline(event) {
        if (this.env.services.pos.numpadMode === 'quantity' && this.env.services.pos.disallowLineQuantityChange()) {
            let order = this.env.services.pos.get_order();
            if(!order.orderlines.length)
                return;
            let selectedLine = order.get_selected_orderline();
            let orderlines = order.orderlines;
            let lastId = orderlines.length !== 0 && orderlines.at(orderlines.length - 1).cid;
            let currentQuantity = this.env.services.pos.get_order().get_selected_orderline().get_quantity();

            if(selectedLine.noDecrease) {
                this.popup.add('ErrorPopup', {
                    title: this.env._t('Invalid action'),
                    body: this.env._t('You are not allowed to change this quantity'),
                });
                return;
            }
            const parsedInput = event.detail.buffer && parse.float(event.detail.buffer) || 0;
            if(lastId != selectedLine.cid)
                this._showDecreaseQuantityPopup();
            else if(currentQuantity < parsedInput)
                this._setValue(event.detail.buffer);
            else if(parsedInput < currentQuantity)
                this._showDecreaseQuantityPopup();
        } else {
            let { buffer } = event.detail;
            let val = buffer === null ? 'remove' : buffer;
            this._setValue(val);
            if (val == 'remove') {
                NumberBuffer.reset();
                this.env.services.pos.numpadMode = 'quantity';
            }
            var a = this.env.services.pos.get_order().get_selected_orderline();
            if(a){
                this.env.services.pos.get_order().set_SearchCostPriceOrder(a.product.standard_price);
            }
        }
    },
});
