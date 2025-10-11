from odoo import models, fields, api,_

class PartnerInh(models.Model):
	_inherit = 'res.partner'

	account_manager_id = fields.Many2one('res.users')
	account_excutive_id = fields.Many2one('res.users')
	account_executive_emp_id = fields.Many2one('hr.employee', "Account Executive")
	marchandiser_id = fields.Many2one('hr.employee')

	merchandiser_id2 = fields.Many2one('res.users', string="Merchandiser2")

	merchandiser_supervisor_id = fields.Many2one('res.users', string="Merchandiser Supervisor")

	cust_sequence = fields.Char()	

	@api.onchange('acc_mnger_history')
	def _compute_current_ac_mngr(self):
		self.account_manager_id = self.env.user
		for line in self.acc_mnger_history:
			if line.end_date == False:
				self.account_manager_id = line.manager.id

	@api.onchange('executive_history')
	def _compute_current_executive(self):
		self.account_excutive_id = self.env.user
		for line in self.executive_history:
			if line.end_date == False:
				self.account_excutive_id = line.exicutive.id

	@api.model
	def create(self, vals):
		"""Creating customer sequence"""
		if "street" in vals:
			if vals.get('is_vendor') == False:
				vals['cust_sequence'] = self.env['ir.sequence'].next_by_code('res.partner') or _('New')
		res = super(PartnerInh, self).create(vals)
		return res

	# @api.model
	# def _name_search(self,name, args=None, operator='ilike', limit=100, name_get_uid=None):
	# 	args = args or []
	# 	domain = []
	# 	if name:
	# 		domain = ['|', '|', ('name',operator,name), ('cust_sequence',operator,name), ('email',operator,name)]
	# 	return self._search(domain + args, limit=limit)

class SaleInh(models.Model):
	_inherit = 'sale.order'

	cust_sequence = fields.Char(related='partner_id.cust_sequence')
