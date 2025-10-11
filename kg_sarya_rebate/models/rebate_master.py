# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
from odoo.tools import float_repr, format_datetime
from odoo.exceptions import ValidationError

class RebateRebate(models.Model):
	_name = "product.rebatelist"

	name = fields.Char()
	rebate_item_ids = fields.One2many(
		'product.rebate.item', 'rebatelist_id', 'Rebate Rules',
		copy=True)
	rebate_type = fields.Selection([('fixed','Fixed'),('progressive','Progressive')],default='fixed')
	company_id = fields.Many2one('res.company')
	currency_id = fields.Many2one('res.currency')
	active = fields.Boolean(default=True)
	total_rebate_percent = fields.Float(compute='get_total_percentage')


	def get_total_percentage(self):
		self.total_rebate_percent = 0.00
		for line in self.rebate_item_ids:
			self.total_rebate_percent = self.total_rebate_percent + line.percent_price



class PartnerRebate(models.Model):
	_inherit = "res.partner"


	rebate_id = fields.Many2one('product.rebatelist')




class RebatelistItem(models.Model):
	_name = "product.rebate.item"
	_description = "Rebate Rule,Condition Under a price list Set various Rebate rule of a Product Category"


	def _default_pricelist_id(self):
		return self.env['product.rebatelist'].search([
			'|', ('company_id', '=', False),
			('company_id', '=', self.env.company.id)], limit=1)

	product_tmpl_id = fields.Many2one(
		'product.template', 'Product', ondelete='cascade', check_company=True,
		help="Specify a template if this rule only applies to one product template. Keep empty otherwise.")
	product_id = fields.Many2one(
		'product.product', 'Product Variant', ondelete='cascade', check_company=True,
		help="Specify a product if this rule only applies to one product. Keep empty otherwise.")
	categ_id = fields.Many2one(
		'product.category', 'Product Category', ondelete='cascade',
		help="Specify a product category if this rule only applies to products belonging to this category or its children categories. Keep empty otherwise.")
	max_quantity = fields.Float(
		'Max. Quantity', default=0, digits="Product Unit Of Measure",
		help="For the rule to apply, bought/sold quantity must be greater "
			 "than or equal to the maximum quantity specified in this field.\n"
			 "Expressed in the default unit of measure of the product.")
	applied_on = fields.Selection([
		('2_product_category', 'Product Category')], "Apply On",
		default='2_product_category', required=True,
		help='Pricelist Item applicable on selected option')
	base = fields.Selection([
		('list_price', 'Sales Price'),
		('standard_price', 'Cost'),
		('pricelist', 'Other Pricelist')], "Based on",
		default='list_price', required=True,
		help='Base price for computation.\n'
			 'Sales Price: The base price will be the Sales Price.\n'
			 'Cost Price : The base price will be the cost price.\n'
			 'Other Pricelist : Computation of the base price based on another Pricelist.')
	base_pricelist_id = fields.Many2one('product.rebatelist', 'Other Pricelist', check_company=True)
	rebatelist_id = fields.Many2one('product.rebatelist', 'Pricelist', index=True, ondelete='cascade', required=True, default=_default_pricelist_id)
	price_surcharge = fields.Float(
		'Price Surcharge', digits='Product Price',
		help='Specify the fixed amount to add or substract(if negative) to the amount calculated with the discount.')
	
	rebate_type = fields.Selection([('fixed','Fixed'),('progressive','Progressive')],related='rebatelist_id.rebate_type')
	price_discount = fields.Float(
		'Price Discount', default=0, digits=(16, 2),
		help="You can apply a mark-up by setting a negative discount.")
	price_round = fields.Float(
		'Price Rounding', digits='Product Price',
		help="Sets the price so that it is a multiple of this value.\n"
			 "Rounding is applied after the discount and before the surcharge.\n"
			 "To have prices that end in 9.99, set rounding 10, surcharge -0.01")
	price_min_margin = fields.Float(
		'Min. Price Margin', digits='Product Price',
		help='Specify the minimum amount of margin over the base price.')
	price_max_margin = fields.Float(
		'Max. Price Margin', digits='Product Price',
		help='Specify the maximum amount of margin over the base price.')
	company_id = fields.Many2one(
		'res.company', 'Company', 
		readonly=True, related='rebatelist_id.company_id', store=True)
	currency_id = fields.Many2one(
		'res.currency', 'Currency',
		readonly=True, related='rebatelist_id.currency_id', store=True)
	active = fields.Boolean(
		readonly=True, related="rebatelist_id.active", store=True)
	date_start = fields.Datetime('Start Date', help="Starting datetime for the rebatelist item validation\n"
												"The displayed value depends on the timezone set in your preferences.")
	date_end = fields.Datetime('End Date', help="Ending datetime for the rebatelist item validation\n"
												"The displayed value depends on the timezone set in your preferences.")
	compute_price = fields.Selection([
		('percentage', 'Discount')], index=True, default='percentage', required=True)
	fixed_price = fields.Float('Fixed Price', digits='Product Price')
	percent_price = fields.Float(
		'Percentage Price',
		help="You can apply a mark-up by setting a negative discount.")
	# functional fields used for usability purposes
	name = fields.Char(
		'Name',compute='_get_pricelist_item_name_price',
		help="Explicit rule name for this rebatelist line.")
	price = fields.Char(
		'Price', compute='_get_pricelist_item_name_price',
		help="Explicit rule name for this rebatelist line.")


	rule_tip = fields.Char(compute='_compute_rule_tip')
	description = fields.Char()


	@api.constrains('base_pricelist_id', 'pricelist_id', 'base')
	def _check_recursion(self):
		if any(item.base == 'pricelist' and item.pricelist_id and item.pricelist_id == item.base_pricelist_id for item in self):
			raise ValidationError(_('You cannot assign the Main Pricelist as Other Pricelist in PriceList Item'))

	@api.constrains('date_start', 'date_end')
	def _check_date_range(self):
		for item in self:
			if item.date_start and item.date_end and item.date_start >= item.date_end:
				raise ValidationError(_('%s : end date (%s) should be greater than start date (%s)', item.display_name, format_datetime(self.env, item.date_end), format_datetime(self.env, item.date_start)))
		return True

	@api.constrains('price_min_margin', 'price_max_margin')
	def _check_margin(self):
		if any(item.price_min_margin > item.price_max_margin for item in self):
			raise ValidationError(_('The minimum margin should be lower than the maximum margin.'))

	@api.constrains('product_id', 'product_tmpl_id', 'categ_id')
	def _check_product_consistency(self):
		for item in self:
			if item.rebate_type == 'progressive':
				if item.applied_on == "2_product_category" and not item.categ_id:
					raise ValidationError(_("Please specify the category for which this rule should be applied"))
				elif item.applied_on == "1_product" and not item.product_tmpl_id:
					raise ValidationError(_("Please specify the product for which this rule should be applied"))

	@api.depends('applied_on', 'categ_id', 'product_tmpl_id', 'product_id', 'compute_price', 'fixed_price', \
		'rebatelist_id', 'percent_price', 'price_discount', 'price_surcharge')
	def _get_pricelist_item_name_price(self):
		"""Setting Name for the applied Field"""
		for item in self:
			if item.categ_id and item.applied_on == '2_product_category':
				item.name = _("Category: %s") % (item.categ_id.display_name)
			elif item.product_tmpl_id and item.applied_on == '1_product':
				item.name = _("Product: %s") % (item.product_tmpl_id.display_name)
			else:
				item.name = _("All Products")

			if item.compute_price == 'fixed':
				decimal_places = self.env['decimal.precision'].precision_get('Product Price')
				if item.currency_id.position == 'after':
					item.price = "%s %s" % (
						float_repr(
							item.fixed_price,
							decimal_places,
						),
						item.currency_id.symbol,
					)
				else:
					item.price = "%s %s" % (
						item.currency_id.symbol,
						float_repr(
							item.fixed_price,
							decimal_places,
						),
					)
			elif item.compute_price == 'percentage':
				item.price = _("%s %% discount", item.percent_price)
			else:
				item.price = _("%(percentage)s %% discount and %(price)s surcharge", percentage=item.price_discount, price=item.price_surcharge)

	@api.depends_context('lang')
	@api.depends('compute_price', 'price_discount', 'price_surcharge', 'base', 'price_round')
	def _compute_rule_tip(self):
		base_selection_vals = {elem[0]: elem[1] for elem in self._fields['base']._description_selection(self.env)}
		self.rule_tip = False
		for item in self:
			if item.compute_price != 'formula':
				continue
			base_amount = 100
			discount_factor = (100 - item.price_discount) / 100
			discounted_price = base_amount * discount_factor
			if item.price_round:
				discounted_price = tools.float_round(discounted_price, precision_rounding=item.price_round)
			surcharge = tools.format_amount(item.env, item.price_surcharge, item.currency_id)
			item.rule_tip = _(
				"%(base)s with a %(discount)s %% discount and %(surcharge)s extra fee\n"
				"Example: %(amount)s * %(discount_charge)s + %(price_surcharge)s → %(total_amount)s",
				base=base_selection_vals[item.base],
				discount=item.price_discount,
				surcharge=surcharge,
				amount=tools.format_amount(item.env, 100, item.currency_id),
				discount_charge=discount_factor,
				price_surcharge=surcharge,
				total_amount=tools.format_amount(
					item.env, discounted_price + item.price_surcharge, item.currency_id),
			)

	@api.onchange('compute_price')
	def _onchange_compute_price(self):
		if self.compute_price != 'fixed':
			self.fixed_price = 0.0
		if self.compute_price != 'percentage':
			self.percent_price = 0.0
		if self.compute_price != 'formula':
			self.update({
				'base': 'list_price',
				'price_discount': 0.0,
				'price_surcharge': 0.0,
				'price_round': 0.0,
				'price_min_margin': 0.0,
				'price_max_margin': 0.0,
			})

	@api.onchange('product_id')
	def _onchange_product_id(self):
		has_product_id = self.filtered('product_id')
		for item in has_product_id:
			item.product_tmpl_id = item.product_id.product_tmpl_id
		if self.env.context.get('default_applied_on', False) == '1_product':
			# If a product variant is specified, apply on variants instead
			# Reset if product variant is removed
			# has_product_id.update({'applied_on': '0_product_variant'})
			(self - has_product_id).update({'applied_on': '1_product'})

	@api.onchange('product_tmpl_id')
	def _onchange_product_tmpl_id(self):
		has_tmpl_id = self.filtered('product_tmpl_id')
		for item in has_tmpl_id:
			if item.product_id and item.product_id.product_tmpl_id != item.product_tmpl_id:
				item.product_id = None

	@api.onchange('product_id', 'product_tmpl_id', 'categ_id')
	def _onchane_rule_content(self):
		if not self.user_has_groups('product.group_sale_pricelist') and not self.env.context.get('default_applied_on', False):
			# If advanced pricelists are disabled (applied_on field is not visible)
			# AND we aren't coming from a specific product template/variant.
			variants_rules = self.filtered('product_id')
			template_rules = (self-variants_rules).filtered('product_tmpl_id')
			# variants_rules.update({'applied_on': '0_product_variant'})
			template_rules.update({'applied_on': '1_product'})
			# (self-variants_rules-template_rules).update({'applied_on': '3_global'})

	@api.model_create_multi
	def create(self, vals_list):
		for values in vals_list:
			if values.get('applied_on', False):
				# Ensure item consistency for later searches.
				applied_on = values['applied_on']
				if applied_on == '2_product_category':
					values.update(dict(product_id=None, product_tmpl_id=None))
				elif applied_on == '1_product':
					values.update(dict(product_id=None, categ_id=None))
				# elif applied_on == '0_product_variant':
				#     values.update(dict(categ_id=None))
		return super(RebatelistItem, self).create(vals_list)

	def write(self, values):
		if values.get('applied_on', False):
			# Ensure item consistency for later searches.
			applied_on = values['applied_on']
			if applied_on == '2_product_category':
				values.update(dict(product_id=None, product_tmpl_id=None))
			elif applied_on == '1_product':
				values.update(dict(product_id=None, categ_id=None))
			# elif applied_on == '0_product_variant':
			#     values.update(dict(categ_id=None))
		res = super(RebatelistItem, self).write(values)
		# When the pricelist changes we need the product.template price
		# to be invalided and recomputed.
		self.flush()
		self.invalidate_cache()
		return res

	def _compute_price(self, price, price_uom, product, quantity=1.0, partner=False):
		"""Compute the unit price of a product in the context of a pricelist application.
		   The unused parameters are there to make the full context available for overrides.
		"""
		self.ensure_one()
		convert_to_price_uom = (lambda price: product.uom_id._compute_price(price, price_uom))
		if self.compute_price == 'fixed':
			price = convert_to_price_uom(self.fixed_price)
		elif self.compute_price == 'percentage':
			price = (price - (price * (self.percent_price / 100))) or 0.0
		# else:
		#     # complete formula
		#     price_limit = price
		#     price = (price - (price * (self.price_discount / 100))) or 0.0
		#     if self.price_round:
		#         price = tools.float_round(price, precision_rounding=self.price_round)

		#     if self.price_surcharge:
		#         price_surcharge = convert_to_price_uom(self.price_surcharge)
		#         price += price_surcharge

		#     if self.price_min_margin:
		#         price_min_margin = convert_to_price_uom(self.price_min_margin)
		#         price = max(price, price_limit + price_min_margin)

		#     if self.price_max_margin:
		#         price_max_margin = convert_to_price_uom(self.price_max_margin)
		#         price = min(price, price_limit + price_max_margin)
		return price


