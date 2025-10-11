from dateutil.relativedelta import relativedelta

from odoo import models, fields, api
from odoo.exceptions import ValidationError

from odoo import http

from datetime import datetime,date


class PricelistItemInherit(models.Model):
	_inherit = "product.pricelist.item"	

	# setting product as default in apply on
	applied_on = fields.Selection([
		('3_global', 'All Products'),
		('2_product_category', 'Product Category'),
		('1_product', 'Product'),
		('0_product_variant', 'Product Variant')], "Apply On",
		default='1_product', required=True,
		help='Pricelist Item applicable on selected option')
	product_price = fields.Float('Product Price', digits='Product Price',compute='_set_price_details')
	final_price = fields.Float('Final Price', digits='Product Price',compute='_set_price_details')
	customer_item_code = fields.Char("Customer Item Code")
	promo = fields.Selection([
		('off', 'Price Off'),
		('comp', 'Price Comp')], "Promotion")
	packging_id = fields.Many2one('product.packaging', "Packaging")

	@api.depends('product_tmpl_id','compute_price','base','fixed_price','percent_price','price_discount','price_surcharge')
	def _set_price_details(self):
		for line in self:
			line.final_price=0.0
			line.product_price=0.0
			if line.product_tmpl_id:
				product_id = self.env['product.template'].search([('id', '=',line.product_tmpl_id.id)])
				if line.base=='list_price':
				   line.product_price=product_id.list_price
				elif line.base=='standard_price':
					line.product_price=product_id.standard_price
				if line.compute_price=='fixed':
					line.final_price=line.fixed_price
				if line.compute_price=='percentage':
					line.final_price=line.product_price-((line.product_price/100)*line.percent_price)
				if line.compute_price=='formula':
					line.final_price=(line.product_price-((line.product_price/100)*line.price_discount))+line.price_surcharge


class ProductPricelistInh(models.Model):
	_inherit = "product.pricelist"

	customer_ids = fields.Many2many('res.partner',string='Customer')
	start_date = fields.Date()
	end_date = fields.Date()
	special = fields.Boolean(string='Special Pricelist', default=False)

	def action_archive_pricelist(self):
		"""This will archive the expired pricelist"""
		price_list = self.env['product.pricelist'].search([('active','=',True),('end_date','!=',False)])
		for plist in price_list:
			if plist.end_date < date.today():
				plist.active = False

class ProductInh(models.Model):
	_inherit = "product.template"

	net_weight = fields.Float()
	gross_weight = fields.Float()
	width = fields.Float(digits = (12,15))
	height = fields.Float(digits = (12,15))
	lenght = fields.Float(digits = (12,15))
	cbm = fields.Float(compute='calculate_cbm',string="CBM",  digits = (12,15))

	@api.depends('height','lenght','width')
	def  calculate_cbm(self):
		for product in self:
			product.cbm = product.width*product.height*product.lenght




