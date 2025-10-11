from odoo import fields, models, api
from odoo.exceptions import UserError
import base64

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    delivery_partner_id = fields.Many2one('res.partner', string="Delivery Partner")
    delivery_doc_number = fields.Char(string="LR No./Delivery Document No.")
    delivery_estimate_amount = fields.Float(string="Estimated Amount(Excluding GST)")
    delivery_actual_amount = fields.Float(string="Actual Amount(Excluding GST)")
    delivery_variation_amount = fields.Float(string="Variation Amount", compute='_compute_variation_amount')
    delivery_partner_status = fields.Selection(
        string='Delivery Partner Status',
        selection=[('pending', 'Pending Delivery'), ('email', 'Email Sent'), ('notify', 'Sent to Finance'),
                   ('posted', 'Posted'), ('variation', 'Variation') ],
        default='pending', )
    delivery_partner_remark = fields.Text(string="Remarks")

    delivery_partner_invoice = fields.Binary(string="Delivery Partner Invoice")
    delivery_move_id = fields.Many2one('account.move', string="Delivery Provision Entry",)
    delivery_partner_region_id = fields.Many2one('account.analytic.account', string="Region")

    def _compute_variation_amount(self):
        for record in self:
            if record.delivery_actual_amount != 0:
                record.delivery_variation_amount = record.delivery_actual_amount - record.delivery_estimate_amount
            else:
                record.delivery_variation_amount = 0.0

    def action_delivery_partner_send_doc(self):
        """Send delivery partner document via email."""
        if not self.delivery_partner_id:
            raise UserError(('Delivery partner missing, Please select a delivery partner before sending the document.'))
        template = self.env.ref('kg_sarya_inventory.email_template_delivery_partner_document')
        # Attach proforma invoice
        report = self.env.ref('sarya_reports.action_report_proforma_invoice')
        pdf_content, _ = report._render_qweb_pdf(report.report_name, res_ids=self.sale_id.id)

        attachment = self.env['ir.attachment'].create({
            'name': f"Proforma_{self.sale_id.name}.pdf",
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': 'stock.picking',  # link to picking for chatter display
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        if template:
            self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True, email_values={'attachment_ids': [attachment.id]})
        self.delivery_partner_status = 'email'
        return True

    def action_delivery_partner_send_finance(self):
        if self.delivery_partner_status == 'email':
            users = self.env.ref('kg_sarya_inventory.delivery_partner_finance_notify').users
            email_to = ""
            for usr in users:
                if usr.partner_id.email:
                    if not email_to:
                        email_to = usr.partner_id.email
                    else:
                        email_to = email_to + ', ' + usr.partner_id.email

            main_content = {
                'subject': ('Delivery Partner Provision: No. %s approval request' % self.name),
                'author_id': self.env.user.partner_id.id,
                'body_html': 'Hi,<br><br>Provision entry for item delivery by %s, Document No.: %s is waiting for your approval.<br><br>SO Number: %s' % (self.delivery_partner_id.name, self.name, self.sale_id.name),
                'email_to': email_to,
            }
            self.env['mail.mail'].sudo().create(main_content).send()
            self.delivery_partner_status = 'notify'

    def action_delivery_partner_post_provision(self):
        """Create and post provision entry for delivery partner"""
        for picking in self:
            company = picking.company_id

            if not picking.delivery_partner_id:
                raise UserError(("Delivery Partner is not set for this picking."))

            if not company.logistic_partner_expense_account_id or not company.logistic_partner_provision_account_id:
                raise UserError(("Please configure Logistic Partner accounts in Company settings."))

            journal = self.env['account.journal'].search(
                [('type', '=', 'general'), ('company_id', '=', company.id)],
                limit=1
            )
            if not journal:
                raise UserError(("No Miscellaneous Journal found for company %s.") % company.name)

            move_vals = {
                'ref': ('Provision for Delivery Charge: %s - %s') % (picking.name, picking.delivery_doc_number or ''),
                'date': picking.scheduled_date or fields.Date.today(),
                'journal_id': journal.id,
                'company_id': company.id,
                'line_ids': [
                    (0, 0, {
                        'account_id': company.logistic_partner_expense_account_id.id,
                        'partner_id': picking.delivery_partner_id.id,
                        'analytic_distribution': {picking.delivery_partner_region_id.id: 100},
                        'name': ('Logistic Expense - %s - %s') % (picking.delivery_doc_number or '', picking.delivery_partner_remark or ' '),
                        'debit': picking.delivery_estimate_amount,
                        'credit': 0.0,
                    }),
                    (0, 0, {
                        'account_id': company.logistic_partner_provision_account_id.id,
                        'partner_id': picking.delivery_partner_id.id,
                        'analytic_distribution': {picking.delivery_partner_region_id.id: 100},
                        'name': ('Logistic Provision - %s - %s') % (picking.delivery_doc_number or '', picking.delivery_partner_remark or ' '),
                        'debit': 0.0,
                        'credit': picking.delivery_estimate_amount,
                    }),
                ]
            }

            move = self.env['account.move'].create(move_vals)
            move.action_post()
            picking.delivery_move_id = move.id

            # Optional: log in chatter
            picking.message_post(
                body=("Provision entry %s created for delivery partner %s for amount %.2f") % (
                    move.name, picking.delivery_partner_id.name, picking.delivery_estimate_amount
                ),
                message_type='comment'
            )
            self.delivery_partner_status = 'posted'


