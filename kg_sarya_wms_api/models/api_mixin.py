# -*- coding: utf-8 -*-
import base64
import logging
from datetime import date

from odoo import models, _
from odoo.exceptions import UserError,ValidationError
import requests
import json

import logging
_logger = logging.getLogger(__name__)


class SaryaWMSAPiMixin(models.AbstractModel):
	""" A mixin to call some logic-oriented functions/methods to communicate with API.
	"""
	_name = 'sarya.wms.api'
	_description = 'Sarya API Mixin'


	def get_token(self):
		"""getting autherization token"""
		if not self.env.company.client_id:
			raise ValidationError("Configure client id in company master")
		if not self.env.company.client_secret:
			raise ValidationError("Configure client secret in company master")
		if not self.env.company.wms_url:
			raise ValidationError("Configure WMS url in company master")
		client_id = bytes(self.env.company.client_id+":", 'utf-8')
		clent_secrt = bytes(self.env.company.client_secret, 'utf-8')
		authorization = base64.b64encode(client_id+clent_secrt)
		str_authorization=str(authorization)
		auth_key = str_authorization.split('\'')[1::2][0]
		headers = {
			"Connection":'keep-alive',
			"Content-Type":'application/json; charset=utf-8',
			"Content-Type":'application/json',
			"Accept":'application/hal+json',
			"Authorization":'Basic '+ auth_key, 
			"Accept-Language":'en-US,en;q=0.8',
			"Content-Length":'113'
		}
		data = {
				"grant_type": "client_credentials",
				"user_login": "ODOO" 
			}
		auth_url = "%s/AuthServer/api/Token" % self.env.company.wms_url
		response = requests.post(auth_url, headers=headers, json=data)
		response_data = response.json()
		auth = "%s %s" % (response_data['token_type'], response_data['access_token'])
		return auth

	def post(self,data=None,url=None):
		"""posting data to WMS"""
		try:
			auth_token = self.get_token()
			self.env.company.auth_token = auth_token
			headers = {
				"Host":'secure-wms.com',
				"Content-Type":'application/json; charset=utf-8',
				"Accept":'application/hal+json',
				"Authorization":auth_token, 
				"Accept-Language":'en-US,en;q=0.8',
				"Content-Length":'1072'
			}
			response = requests.post(url, headers=headers, json=data)
		except:
			raise ValidationError("Something went wrong!!")
		if 'ErrorCode' in response.json():
			self.handle_error(response)
		return response



	def get_details(self,url=None):
		"""Getting details from WMS"""
		auth_token = self.get_token()
		headers = {
			"Host":'box.secure-wms.com',
			"Content-Type":'application/json; charset=utf-8',
			"Accept":'application/hal+json',
			"Authorization":auth_token, 
			"Accept-Language":'en-US,en;q=0.8',
			"Accept-Encoding":'gzip,deflate,sdch',
		}
		response = requests.get(url, headers=headers)
		if 'ErrorCode' in response.json():
			self.handle_error(response)
		return response
	   
	def purchase_shipment(self,url=None,data_list=False,ship_obj=False):
		"""Passing data to WMS receive menu"""
		auth_token = self.get_token()
		headers = {
			"Host":'box.secure-wms.com',
			"Content-Type":'application/json; charset=utf-8',
			"Accept":'application/hal+json',
			"Authorization":auth_token, 
			"Accept-Language":'en-US,en;q=0.8',
			"Accept-Encoding":'gzip,deflate,sdch',
			"Content-Length":'1072'
		}
		# data = {
		#     "customerIdentifier": {
		#         "id": str(self.env.company.customer_id)
		#     },
		#     "facilityIdentifier": {
		#         "id": str(self.env.company.facility_id)
		#     },
		#     "referenceNum": str(ship_obj.bill_no),
		#     "notes": "Warehouse Instructions",
		#     "shippingNotes": "Carrier specific shipping instructions",
		#     "billingCode": "Prepaid",
		#     "asnNumber": "ASN123",
		#     "routingInfo": {
		#         "carrier": "UPS",
		#         "mode": "92",
		#         "scacCode": "UPGN",
		#         "account": "12345z"
		#     },
		#     "shipTo": {
		#         "companyName": "3PLCentral",
		#         "name": "test",
		#         "address1": "222 N PCH HWY",
		#         "address2": "Suite 1500",
		#         "city": "EL Segundo",
		#         "state": "CA",
		#         "zip": "90245",
		#         "country": "US"
		#     },
		#     "orderItems": data_list
		# }
		data = {
			"customerIdentifier": { 
				# "externalId": "str",
				# "name": "str",
				"id": str(self.env.company.customer_id)
			},
			"facilityIdentifier": { 
				# "name": "str",
				"id": str(self.env.company.facility_id)
			},
			"transactionEntryType": 0,
			"importModuleId": 1,
			"referenceNum": str(ship_obj.name), 
			"arrivalDate": str(ship_obj.arrival_date) if ship_obj.arrival_date else str(date.today()),
			"expectedDate": str(ship_obj.expected_date) if ship_obj.expected_date else str(date.today()),
			"receiptAdviceNumber":str(ship_obj.shipment_no),
			"notes": str(ship_obj.notes),
			"receiveItems": data_list,
		}
		response = requests.post(url, headers=headers, json=data)
		if 'ErrorCode' in response.json():
			print(response.json())
			self.handle_error(response)
		return response


	   
	def delivery_order(self,url=None,data_list=False,stock_obj=False):
		"""Passing data to WMS order menu"""
		auth_token = self.get_token()
		headers = {
			"Host":'box.secure-wms.com',
			"Content-Type":'application/json; charset=utf-8',
			"Accept":'application/hal+json',
			"Authorization":auth_token, 
			"Accept-Language":'en-US,en;q=0.8',
			"Accept-Encoding":'gzip,deflate,sdch',
			"Content-Length":'1072'
		}
		data = {
		    "customerIdentifier": {
		        "id": str(self.env.company.customer_id)
		    },
		    "facilityIdentifier": {
		        "id": str(self.env.company.facility_id)
		    },
		    "referenceNum": str(stock_obj.name),
		    "notes": str(stock_obj.note),
		    # "shippingNotes": "Carrier specific shipping instructions",
		    # "billingCode": "Prepaid",
		    # "asnNumber": "ASN123",
		    # "routingInfo": {
		    #     "carrier": "UPS",
		    #     "mode": "92",
		    #     "scacCode": "UPGN",
		    #     "account": "12345z"
		    # },
		    "shipTo": {
		        "companyName": str(stock_obj.partner_id.name) if stock_obj.partner_id.name else '',
		        "name": str(stock_obj.partner_id.name)  if stock_obj.partner_id.name else '',
		        "address1": str(stock_obj.partner_id.street)  if stock_obj.partner_id.street else '',
		        "address2": str(stock_obj.partner_id.street2)  if stock_obj.partner_id.street2 else '',
		        "city": str(stock_obj.partner_id.city)  if stock_obj.partner_id.city else '',
		        "state": str(stock_obj.partner_id.state_id.name)  if stock_obj.partner_id.state_id.name else '',
		        "zip":  str(stock_obj.partner_id.zip)  if stock_obj.partner_id.zip else '',
		        "country": str(stock_obj.partner_id.country_id.name)  if stock_obj.partner_id.country_id.name else ''
		    },
		    "orderItems": data_list
		}
		response = requests.post(url, headers=headers, json=data)
		if 'ErrorCode' in response.json():
			response_data = response.json()
			res_property = response_data['Properties'][0]
			if response_data['ErrorCode'] == "Duplicate" and "WH" in res_property['Value']:
				pass 
			else:
				self.handle_error(response)
			# self.handle_error(response)
		return response

	def handle_error(self,response):
		"""Response error handling"""
		response_data = response.json()
		res_property = response_data['Properties'][0]
		raise ValidationError(_("ErrorCode:%s in WMS") % (response_data['ErrorCode']))

		# print(response_data['Properties'])


