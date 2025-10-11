# -*- coding: utf-8 -*-

from odoo import models, fields, _, api


class ShipmentAdviceConfig(models.Model):

    _name = 'shipment.advice.config'


    email_for_3pl = fields.Char("Email for 3PL notification")
    email_for_grn_verification = fields.Char("Email for GRN Verification")
    email_for_recheck_verification = fields.Char("Email for Recheck Verification")
    email_for_grn_completed = fields.Char("Email for GRN Completed")


    def get_email_for_grn_completed(self):
        email = ""
        config = self.search([], limit=1)
        if config:
            email = config.email_for_grn_completed
        return email



    def get_email_for_3pl(self):
        email = ""
        config = self.search([], limit=1)
        if config:
            email = config.email_for_3pl
        return email


    def get_email_for_grn_verification(self):
        email = ""
        config = self.search([], limit=1)
        if config:
            email = config.email_for_grn_verification
        return email


    def get_email_for_recheck_verification(self):
        email = ""
        config = self.search([], limit=1)
        if config:
            email = config.email_for_recheck_verification
        return email
