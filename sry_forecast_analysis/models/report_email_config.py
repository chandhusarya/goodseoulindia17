# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import models, fields, _, api
import base64

class ReportEmailConfig(models.Model):
    _name = 'report.email.config'


    soh_email = fields.Char("SOH Email")
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company')


    def button_generate_soh(self):
        return self.env.ref('sry_forecast_analysis.report_sohreport').report_action(self)

    def send_email_with_excel_attach(self):
        config = self.search([], limit=1)
        if not config:
            return
        company_ids = self.env['res.company'].sudo().search([]).ids
        context = dict(self.env.context, company_ids=company_ids)
        report = self.env.ref('sry_forecast_analysis.report_sohreport')
        generated_report = report._render_xlsx('sry_forecast_analysis.report_sohreport', [self.id], data={'company_ids':company_ids})
        data_record = base64.b64encode(generated_report[0])
        formatted_date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mail_subj = f"Good Seoul India Stock On Hand Report as on {formatted_date_time}"
        mail_content = f"Hello,<br>Attached Stock On Hand Report as on {formatted_date_time}"
        main_content = {
            'subject': mail_subj,
            'body_html': mail_content,
            'email_to': config.soh_email,
            'attachment_ids': [(0, 0, {
                'name': 'INDIA_SOH_Report.xlsx',
                'datas': data_record,
                'type': 'binary',
            })],
        }
        self.env['mail.mail'].sudo().create(main_content).send()




