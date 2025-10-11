# -*- coding: utf-8 -*-

from odoo import models, fields,api,_
import requests
from odoo.exceptions import UserError,ValidationError
from datetime import datetime, timedelta,date
import time


class ShipmentAdv(models.Model):
	_inherit = 'shipment.advice'




class ShipmentAdviceTotal(models.Model):
	_inherit = 'shipment.advice.summary'







