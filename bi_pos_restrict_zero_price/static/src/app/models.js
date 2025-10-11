/** @odoo-module */

import { Order, Orderline, Payment } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { _t } from "@web/core/l10n/translation";
// New orders are now associated with the current table, if any.
patch(Order.prototype, {
   async pay() {
   
        let self = this;
        let order = this.pos.get_order();
        let lines = order.get_orderlines();
        let restrict_order = false;
        var product_names = ''
        if (this.env.services.pos.config.restrict_zero_price_line){
            if (order && lines.length > 0 ){
                lines.forEach(function (line){
                    if (line.get_display_price() == 0.00){
                       restrict_order = true;
                       product_names += '-' + line.product.display_name + "\n"
                    }
                });
            }
            else
            {
                 restrict_order = true;
            }
            if (restrict_order){
                if (product_names){
                    self.env.services.popup.add(ErrorPopup, {
                        'title': _t("Product With 0 Price"),
                        'body':  _t('You are not allowed to have the zero prices on the order line . %s',product_names),

                    });
                }
                else{
                     self.env.services.popup.add(ErrorPopup, {
                        'title': _t("Empty Order"),
                        'body': _t('There must be at least one product in your order before it can be validated.'),

                    });
                }
            }
            else{
                super.pay();
            }
        }
        else{
            super.pay();
        }
    },

});