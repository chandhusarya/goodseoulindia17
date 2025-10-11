/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
  async _processData(loadedData) {
    await super._processData(...arguments);
    var self = this;
    self.suggestions = loadedData["product.suggestion"] || [];

    self.suggestions = JSON.parse(JSON.stringify(self.suggestions));
    self.suggestion = {};
    for (let suggestion of self.suggestions) {
      self.suggestion[suggestion.id] = suggestion;
    }
  },
});
