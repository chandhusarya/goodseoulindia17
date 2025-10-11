from odoo import fields, models, api, _


class Sale(models.Model):
    _inherit = 'sale.order'

    def send_quotation_approval_email(self):
        responsibles = self.env.company.quote_approval_mail_users_ids
        if not responsibles:
            return
        email_list = ",".join(user.partner_id.email for user in responsibles if user.partner_id.email)
        mail_content = "Dear User,<br><br>" + str(self.partner_id.name) + " have created a new quotation(<b>"+ self.name +"</b>) from portal." + "<br>Kindly review and confirm the same."
        main_content = {
            'subject': _('New Quotation Generated in Portal ' + str(self.name)),
            'body_html': mail_content,
            'email_to': email_list,
            'reply_to': 'erp@sarya.ae',
        }
        self.env['mail.mail'].create(main_content).send()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def write(self, values):
        res = super(SaleOrderLine, self).write(values)
        if 'price_unit' in values:
            print("values ====================>> ", values)

        return res
