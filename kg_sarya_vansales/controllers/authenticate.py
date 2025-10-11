# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import Session
import string
import secrets
from datetime import datetime

class LoginAuthentication(Session):

	@http.route('/web/session/authenticate', type='json', auth="none")
	def authenticate(self, db, login, password, base_location=None):
		"""Creating token and passing with login details and also storing details in history table"""
		res = super(LoginAuthentication, self).authenticate(db, login, password, base_location=None)
		alphabet = string.ascii_letters + string.digits
		while True:
			token = ''.join(secrets.choice(alphabet) for i in range(10))
			if (any(c.islower() for c in token) and any(c.isupper() for c in token) and sum(c.isdigit() for c in token) >= 3):
				break
		histry = request.env['user.login.history'].search([('user','=',res['uid']),('active','=',True)])
		if histry:
			histry.active = False
		request.env['user.login.history'].create({'token':token,'user':res['uid'],'active':True,'login_time':datetime.now()})
		res['token'] = token
		return res