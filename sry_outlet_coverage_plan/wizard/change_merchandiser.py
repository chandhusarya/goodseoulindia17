from odoo import models, fields, api,_

class change_merchandiser(models.TransientModel):
    _name = 'change.merchandiser.wizard'

    partner_id = fields.Many2one('res.partner', string="Outlet")
    merchandiser_id2 = fields.Many2one('res.users', string="Merchandiser")

    def change_merchandiser(self):

        merchandiser_name = ""
        if self.merchandiser_id2:
            self.partner_id.merchandiser_id2 = self.merchandiser_id2.id
            merchandiser_name = self.merchandiser_id2.name
        else:
            self.partner_id.merchandiser_id2 = False

        msg = "Updated Merchandiser to %s" % merchandiser_name
        self.partner_id.message_post(body=msg)