# -*- coding: utf-8 -*-

from odoo import models, fields,api,_
import requests
from odoo.exceptions import UserError,ValidationError

class ProductProduct(models.Model):
	_inherit = 'product.product'

	wms_product_id = fields.Integer('WMS Product ID')

	# @api.model
	# def create(self, vals):
	# 	url = "%s/customers/%s/items" % (self.env.company.wms_url,self.env.company.customer_id)
	# 	product_tmpl_id = vals['product_tmpl_id']
	# 	prduct_temp = self.env['product.template'].search([('id','=',product_tmpl_id)])
	# 	pkg_unit =""
	# 	pkg_qty =0.0
	# 	upc = ""
	# 	for package in prduct_temp.packaging_ids:
	# 		if package.purchase:
	# 			pkg_unit = package.name
	# 			pkg_qty = package.qty
	# 			upc = package.barcode if package.barcode else ''
	# 			break;
	# 	# print(prduct_temp.image_1920)
	# 	# print(type(prduct_temp.image_1920))
	# 	data = {
	# 	      "sku": prduct_temp.default_code,
	# 	      "description": prduct_temp.name,
	# 		  "cost": prduct_temp.standard_price,
	# 		  "price":prduct_temp.list_price,
	# 	      "options": {
	# 	      "inventoryUnit": {
	# 	          "unitIdentifier": {
	# 	          "name": "EACH"
	# 	          }
	# 	            },
	# 	        "secondaryUnit": {
	# 	            "inventoryAlso": 'true',
	# 	            "unitIdentifier": {
	# 	                "name": pkg_unit,
		              
	# 	            },
	# 	            "inventoryUnitsPerUnit": pkg_qty
	# 	        },
		#         "packageUnit": {
		#         	   "imperial": {
		#                 "netWeight": prduct_temp.weight,
		#                 "length": prduct_temp.lenght,
		#                 "width": prduct_temp.width,
		#                 "height": prduct_temp.height,
		#                 "weight": prduct_temp.gross_weight,
  #           		},
		#             "upc": upc,
		#             "unitIdentifier": {
		#                 "name":pkg_unit,
		#             },
		#             "inventoryUnitsPerUnit": pkg_qty
		#         },
		#         "trackBys": {
		#             "trackLotNumber": 0,
		#             "trackSerialNumber": 0,
		#             "trackExpirationDate": 1,
		#             "trackCost": 0,
		#             "outboundMobileSerialization": 0,
		#             "autoHoldExpirationDaysThreshold":prduct_temp.expiration_time,
		#             "isPickLotNumberRequired": 'true',
		#             "isPickSerialNumberRequired": 'true',
		#             "isPickExpirationDateRequired": 'true'
		#         },
		#     },
		    
		#     "_embedded": [{
		#         "item": [
		#             {
		#                 "qualifier": "FROZEN"
		#             }
		#         ]
		#     }]
		#   }

		# response_data = self.env['sarya.wms.api'].post(data,url)
		# response = response_data.json()
		# wms_product_id = response['itemId']
		# vals['wms_product_id']= wms_product_id
		# prduct_temp.wms_product_id = wms_product_id
		# res = super(ProductProduct, self).create(vals)
		# return res

class ProductTemplate(models.Model):
	_inherit = 'product.template'

	wms_product_id = fields.Integer('WMS Product ID',)

	def get_wms_details(self):
		if self.wms_product_id == 0:
			raise ValidationError("No Record found in WMS")
		else:

			url = "%s/inventory/stocksummaries?rql=itemid==%s" % (self.env.company.wms_url,self.wms_product_id)
			response_data = self.env['sarya.wms.api'].get_details(url)
			data_dict = response_data.json()
			if data_dict["totalResults"] == 0:
				raise ValidationError("No Stock Summery Available for this Product")
			else:
				result_dict = data_dict["summaries"][0]
				created_popup = self.env['wms.stock.details'].create({'total_received':result_dict["totalReceived"],'allocated':result_dict["allocated"],'available':result_dict["available"],'on_hold':result_dict["onHold"],'on_hand':result_dict["onHand"],'wms_product_id':self.wms_product_id}).id
				return {
					'name': _('WMS STOCK DETAILS..!'),
					'type': 'ir.actions.act_window',
					'view_mode': 'form',
					'view_type': 'form',
					'res_model': 'wms.stock.details',
					'res_id': created_popup,
					'views':[(self.env.ref('kg_sarya_wms_api.view_wms_stock_details').id,'form')],
					'view_id': self.env.ref('kg_sarya_wms_api.view_wms_stock_details').id,
					'target': 'new'
					}				

				
				


		# getting details 
		# setting url for diff cases
		# by item id
		# if not self.env.company.customer_id:
		# 	raise ValidationError("Configure customer id in company master")
		# if not self.env.company.facility_id:
		# 	raise ValidationError("Configure facility id in company master")
		# wms_product_id = 847
		# url = "https://box.secure-wms.com/inventory/stocksummaries?rql=itemid==%s" % wms_product_id
		# print(url)		
		# response_data = self.env['sarya.wms.api'].get_details(url)
		# print(response_data.text)
		# print("---------------------------------------------")

		# whole details by customer and facilities
		# url = "https://box.secure-wms.com/inventory/stockdetails?customerid=%s&facilityid=%s" % (self.env.company.customer_id,self.env.company.facility_id)
		# response_data = self.env['sarya.wms.api'].get_details(url)
		# print(response_data.text)


