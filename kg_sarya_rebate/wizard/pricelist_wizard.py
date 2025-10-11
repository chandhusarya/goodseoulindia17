from odoo import models, fields, api,_
from odoo.exceptions import ValidationError


class PricelistWizard(models.TransientModel):
	_name = 'pricelist.wizard'
	_description = 'Loading Product for Pricelist'

	product_type = fields.Selection([('all_product','All Product'),('selected','Selected Product')],default='all_product')	
	rebate_id = fields.Many2one('rebate.master')
	brand_id = fields.Many2many('product.manufacturer')
	customer_section_id = fields.Many2one('customer.section')
	price_list = fields.Many2one('product.pricelist')
	product_ids = fields.One2many( 'pricelist.product.line', 'pricelist_wizard_id', 'Prodct Line',copy=True)
	company_id = fields.Many2one('res.company')	
	pricelist_name = fields.Char()



	def create_price_list(self):
		"""creating or updating price list"""
		status = 0
		for el in self.product_ids:
			if el.price != 0.0:
				status =1
		if status == 0:
			raise ValidationError(_("Please update the price"))
		if not self.price_list:
			price_list = self.env['product.pricelist'].create({'company_id':self.company_id.id,'name':self.pricelist_name})
			details_list = []
			for product in self.product_ids:
				details_list.append((0, 0, {'packging_id':product.packging_id.id,'rebate_id':self.rebate_id.id,'compute_price':'fixed','fixed_price':product.price,'applied_on':'1_product','product_tmpl_id':product.product_id.id}))
			price_list.item_ids = details_list
		else:
			details_list = []
			for product in self.product_ids:
				details_list.append((0, 0, {'packging_id':product.packging_id.id,'rebate_id':self.rebate_id.id,'compute_price':'fixed','fixed_price':product.price,'applied_on':'1_product','product_tmpl_id':product.product_id.id}))
			self.price_list.item_ids = details_list	
		self.rebate_id.status = True	
				
	@api.onchange('brand_id')
	def onchangebrand(self):
		res = {}
		rebate = self.env['rebate.master'].browse(self._context.get('active_ids', []))
		self.product_ids =False
		products = self.env['product.template'].search([('brand','in',self.brand_id.ids),('section','=',self.customer_section_id.id)])
		details_list = []
		for product in products:
			details_list.append((0, 0, {'product_id':product.id}))
		self.product_ids = details_list	
		res['domain']={'brand_id':[('id','in',rebate.brand_id.ids)]}	
		return res


class PricelistProduct(models.TransientModel):
	_name = 'pricelist.product.line'
	_description = 'Loading Product for Pricelist'

	product_id = fields.Many2one('product.template')
	product_product_id = fields.Many2many('product.product')
	price = fields.Float()
	pricelist_wizard_id = fields.Many2one('pricelist.wizard')
	packging_id = fields.Many2one('product.packaging')