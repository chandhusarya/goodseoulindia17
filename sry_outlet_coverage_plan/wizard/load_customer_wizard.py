from odoo import models, fields, api,_

class sry_customer_load_wizard(models.TransientModel):
    _name = 'sry.customer.load.wizard'


    partner_ids = fields.Many2many('res.partner', string='Partners', domain="[('customer_rank','>',0)]")

    def button_load_customers(self):
        coverage_id = self.env.context.get('active_id')

        for partner in self.partner_ids:
            self.env['sry.coverage.master.line'].create({
                'coverage_id': coverage_id,
                'outlet_id': partner.id,
            })



