# -*- coding: utf-8 -*-

from odoo import models, fields,api,_
import requests
from odoo.exceptions import UserError,ValidationError


class StockDelivery(models.Model):
	_inherit = 'stock.picking'

	# def button_validate(self):
	# 	stock_obj = self
	# 	res = super(StockDelivery, self).button_validate()
	# 	order_list = []
	# 	for line in self.move_line_ids_without_package:
	# 		pr_dict = {
	# 		"itemIdentifier": {
	# 			"sku": line.product_id.product_tmpl_id.default_code
	# 		},
	# 		"qty": line.qty_done if line.qty_done != 0 else line.product_uom_qty,
	# 		}
	# 		order_list.append(pr_dict)
	# 	url = "%s/orders" % (self.env.company.wms_url)
	# 	response_data = self.env['sarya.wms.api'].delivery_order(url,order_list,stock_obj)
	# 	return res

