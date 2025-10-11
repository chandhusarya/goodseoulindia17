
import logging
_logger = logging.getLogger(__name__)

from odoo import models, fields, api,_
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

import base64
import io
import csv

FREQUENCY_SELECTION = [
    ('7d', 'Every 7 Days'),
    ('14d', 'Every 14 Days'),
    ('mo', 'Monthly'),
]

class sryCoverageMaster(models.Model):
    _name = 'sry.coverage.master'
    _description = 'Coverage Master'


    name = fields.Char("Name")

    from_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")
    coverage_line = fields.One2many('sry.coverage.master.line', 'coverage_id')

    import_file = fields.Binary(string='File to import route Plan')
    import_filename = fields.Char(string='File Name', store=True)

    plan_of = fields.Selection([('merchandiser', 'Merchandiser'), ('executive', 'Key Account Executive')],
                               string="Plan Of")

    import_msg_log = fields.Text("Import msg log")


    def button_load_customers(self):
        ctx = self._context.copy()
        return {
                'name': _('Load Customers'),
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': self.env.ref('sry_outlet_coverage_plan.sry_customer_load_wizard_view').id,
                'res_model': 'sry.customer.load.wizard',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': ctx,
        }

    def button_apply(self):

        plan = self.env['sry.coverage.plan'].search([('coverage_id', '=', self.id)])
        if plan:
            plan.unlink()

        # Every 7 days Delivery
        self.coverage_line.filtered(lambda x: x.mon_plan == '7d').get_updation_data_delivery(days_addition=7, week_day=0, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.tue_plan == '7d').get_updation_data_delivery(days_addition=7, week_day=1, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.wed_plan == '7d').get_updation_data_delivery(days_addition=7, week_day=2, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.thu_plan == '7d').get_updation_data_delivery(days_addition=7, week_day=3, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.fri_plan == '7d').get_updation_data_delivery(days_addition=7, week_day=4, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.sat_plan == '7d').get_updation_data_delivery(days_addition=7, week_day=5, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.sun_plan == '7d').get_updation_data_delivery(days_addition=7, week_day=6, from_date=self.from_date, to_date=self.to_date)

        # Every 14 days Delivery
        self.coverage_line.filtered(lambda x: x.mon_plan == '14d').get_updation_data_delivery(days_addition=14, week_day=0, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.tue_plan == '14d').get_updation_data_delivery(days_addition=14, week_day=1, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.wed_plan == '14d').get_updation_data_delivery(days_addition=14, week_day=2, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.thu_plan == '14d').get_updation_data_delivery(days_addition=14, week_day=3, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.fri_plan == '14d').get_updation_data_delivery(days_addition=14, week_day=4, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.sat_plan == '14d').get_updation_data_delivery(days_addition=14, week_day=5, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.sun_plan == '14d').get_updation_data_delivery(days_addition=14, week_day=6, from_date=self.from_date, to_date=self.to_date)

        # Monthly delivery
        self.coverage_line.filtered(lambda x: x.mon_plan == 'mo').get_updation_data_delivery(days_addition=30, week_day=0, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.tue_plan == 'mo').get_updation_data_delivery(days_addition=30, week_day=1, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.wed_plan == 'mo').get_updation_data_delivery(days_addition=30, week_day=2, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.thu_plan == 'mo').get_updation_data_delivery(days_addition=30, week_day=3, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.fri_plan == 'mo').get_updation_data_delivery(days_addition=30, week_day=4, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.sat_plan == 'mo').get_updation_data_delivery(days_addition=30, week_day=5, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.sun_plan == 'mo').get_updation_data_delivery(days_addition=30, week_day=6, from_date=self.from_date, to_date=self.to_date)



        # Every 7 days Visit
        self.coverage_line.filtered(lambda x: x.mon_visit_plan == '7d').get_updation_data_visit(days_addition=7, week_day=0, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.tue_visit_plan == '7d').get_updation_data_visit(days_addition=7, week_day=1, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.wed_visit_plan == '7d').get_updation_data_visit(days_addition=7, week_day=2, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.thu_visit_plan == '7d').get_updation_data_visit(days_addition=7, week_day=3, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.fri_visit_plan == '7d').get_updation_data_visit(days_addition=7, week_day=4, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.sat_visit_plan == '7d').get_updation_data_visit(days_addition=7, week_day=5, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.sun_visit_plan == '7d').get_updation_data_visit(days_addition=7, week_day=6, from_date=self.from_date, to_date=self.to_date)

        # Every 14 days Visit
        self.coverage_line.filtered(lambda x: x.mon_visit_plan == '14d').get_updation_data_visit(days_addition=14, week_day=0, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.tue_visit_plan == '14d').get_updation_data_visit(days_addition=14, week_day=1, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.wed_visit_plan == '14d').get_updation_data_visit(days_addition=14, week_day=2, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.thu_visit_plan == '14d').get_updation_data_visit(days_addition=14, week_day=3, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.fri_visit_plan == '14d').get_updation_data_visit(days_addition=14, week_day=4, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.sat_visit_plan == '14d').get_updation_data_visit(days_addition=14, week_day=5, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.sun_visit_plan == '14d').get_updation_data_visit(days_addition=14, week_day=6, from_date=self.from_date, to_date=self.to_date)

        # Monthly Visit
        self.coverage_line.filtered(lambda x: x.mon_visit_plan == 'mo').get_updation_data_visit(days_addition=30, week_day=0, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.tue_visit_plan == 'mo').get_updation_data_visit(days_addition=30, week_day=1, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.wed_visit_plan == 'mo').get_updation_data_visit(days_addition=30, week_day=2, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.thu_visit_plan == 'mo').get_updation_data_visit(days_addition=30, week_day=3, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.fri_visit_plan == 'mo').get_updation_data_visit(days_addition=30, week_day=4, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.sat_visit_plan == 'mo').get_updation_data_visit(days_addition=30, week_day=5, from_date=self.from_date, to_date=self.to_date)
        self.coverage_line.filtered(lambda x: x.sun_visit_plan == 'mo').get_updation_data_visit(days_addition=30, week_day=6, from_date=self.from_date, to_date=self.to_date)



    def import_data_from_csv(self):
        self.coverage_line.unlink()
        self.import_msg_log = ""
        plan = self.env['sry.coverage.plan'].search([('coverage_id', '=', self.id)])
        if plan:
            plan.unlink()

        csv_data = base64.b64decode(self.import_file)
        data_file = io.StringIO(csv_data.decode("unicode_escape"))
        data_file.seek(0)
        reader = csv.DictReader(data_file)

        missing_partner = []
        coverage_line = []

        for row in reader:
            code = row.get('CUSTOMER CODE')
            if code and code != 'NO CODE':
                code = code.zfill(5)
                partner = self.env['res.partner'].search([('cust_sequence', '=', code)])
                if not partner:
                    name = row.get("CUSTOMER", '')
                    missing_partner.append([code, name])
                else:
                    short_code = row.get("CUSTOMER NAME - 14 DIGIT", "")
                    short_code = short_code.strip()
                    if short_code:
                        partner.short_name_merchandiser = short_code

                    selection_option = {'AFTER 7 DAYS' : '7d',
                                        'AFTER 14 DAYS' : '14d',
                                        'Monthly' : 'mo',
                                        'Every 7 days' : '7d',
                                        'EVERY 14 DAYS' : '14d',
                                        'EVERY 7 DAYS' : '7d',
                                        'MONTHLY 1 DAYS' : 'mo'
                                        }

                    vals = {'outlet_id' : partner.id}

                    #Updating Delivery Plan

                    mon_plan = "WEEK 1 DEL- MON"
                    if row.get(mon_plan):
                        vals['mon_plan'] = selection_option[row.get(mon_plan)]

                    tue_plan = "WEEK 1 DEL- TUE"
                    if row.get(tue_plan):
                        vals['tue_plan'] = selection_option[row.get(tue_plan)]

                    wed_plan = "WEEK 1  DEL- WED"
                    if row.get(wed_plan):
                        vals['wed_plan'] = selection_option[row.get(wed_plan)]

                    thu_plan = "WEEK 1  DEL- THU"
                    if row.get(thu_plan):
                        vals['thu_plan'] = selection_option[row.get(thu_plan)]

                    fri_plan = "WEEK 1 DEL- FRI"
                    if row.get(fri_plan):
                        vals['fri_plan'] = selection_option[row.get(fri_plan)]

                    sat_plan = "WEEK 1 DEL- SAT"
                    if row.get(sat_plan):
                        vals['sat_plan'] = selection_option[row.get(sat_plan)]

                    sun_plan = "WEEK 1 DEL- SUN"
                    if row.get(sun_plan):
                        vals['sun_plan'] = selection_option[row.get(sun_plan)]


                    # Updating Visit Plan
                    v_mon_plan = "MER- MON"
                    if row.get(v_mon_plan):
                        vals['mon_visit_plan'] = selection_option[row.get(v_mon_plan)]

                    v_tue_plan = "MER- TUE"
                    if row.get(v_tue_plan):
                        vals['tue_visit_plan'] = selection_option[row.get(v_tue_plan)]

                    v_wed_plan = "MER- WED"
                    if row.get(v_wed_plan):
                        vals['wed_visit_plan'] = selection_option[row.get(v_wed_plan)]

                    v_thu_plan = "MER- THU"
                    if row.get(v_thu_plan):
                        vals['thu_visit_plan'] = selection_option[row.get(v_thu_plan)]

                    v_fri_plan = "MER- FRI"
                    if row.get(v_fri_plan):
                        vals['fri_visit_plan'] = selection_option[row.get(v_fri_plan)]

                    v_sat_plan = "MER- SAT"
                    if row.get(v_sat_plan):
                        vals['sat_visit_plan'] = selection_option[row.get(v_sat_plan)]

                    v_sun_plan = "MER- SUN"
                    if row.get(v_sun_plan):
                        vals['sun_visit_plan'] = selection_option[row.get(v_sun_plan)]

                    vals['coverage_id'] = self.id

                    self.env['sry.coverage.master.line'].create(vals)

        print('\n\n\nmissing_partner ==>> ', missing_partner)

        if missing_partner:
            missing_partner_txt = str(missing_partner)
            import_msg_log = "Missing Customer : %s" % (missing_partner_txt)
            self.import_msg_log = import_msg_log






class sryCoverageMasterLine(models.Model):
    _name = 'sry.coverage.master.line'
    _description = 'Coverage Master Line'

    coverage_id = fields.Many2one('sry.coverage.master')
    outlet_id = fields.Many2one('res.partner')

    merchandiser_id2 = fields.Many2one('res.users', string="Merchandiser2", related="outlet_id.merchandiser_id2")

    account_excutive_id = fields.Many2one('res.users', string="Key Account Executive", related="outlet_id.account_excutive_id")

    account_manager_id = fields.Many2one('res.users', string="Key Account Manager", related="outlet_id.account_manager_id")

    mon_plan = fields.Selection(FREQUENCY_SELECTION, string='D Mon')
    tue_plan = fields.Selection(FREQUENCY_SELECTION, string='D Tue')
    wed_plan = fields.Selection(FREQUENCY_SELECTION, string='D Wed')
    thu_plan = fields.Selection(FREQUENCY_SELECTION, string='D Thurs')
    fri_plan = fields.Selection(FREQUENCY_SELECTION, string='D Fri')
    sat_plan = fields.Selection(FREQUENCY_SELECTION, string='D Sat')
    sun_plan = fields.Selection(FREQUENCY_SELECTION, string='D Sun')

    mon_visit_plan = fields.Selection(FREQUENCY_SELECTION, string='V Mon')
    tue_visit_plan = fields.Selection(FREQUENCY_SELECTION, string='V Tue')
    wed_visit_plan = fields.Selection(FREQUENCY_SELECTION, string='V Wed')
    thu_visit_plan = fields.Selection(FREQUENCY_SELECTION, string='V Thurs')
    fri_visit_plan = fields.Selection(FREQUENCY_SELECTION, string='V Fri')
    sat_visit_plan = fields.Selection(FREQUENCY_SELECTION, string='V Sat')
    sun_visit_plan = fields.Selection(FREQUENCY_SELECTION, string='V Sun')



    def change_merchandiser(self):
        ctx = self._context.copy()
        wizard = self.env['change.merchandiser.wizard'].create({'partner_id' : self.outlet_id.id,
                                                                'merchandiser_id2' : self.outlet_id.merchandiser_id2 and \
                                                                                     self.outlet_id.merchandiser_id2.id \
                                                                                     or False})

        return {
                'name': _('Change Merchandiser'),
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': self.env.ref('sry_outlet_coverage_plan.change_merchandiser_wizard_view').id,
                'res_model': 'change.merchandiser.wizard',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': ctx,
                'res_id' : wizard.id
        }


    def recompute_line(self):
        for line in self:
            plans =  self.env['sry.coverage.plan'].search([('cover_line_id', '=', line.id)])
            if plans:
                plans.unlink()

            from_date = line.coverage_id.from_date
            to_date = line.coverage_id.to_date

            days_addition_map = {'7d' : 7,
                                 '14d' : 14,
                                 'mo' : 30}
            if line.mon_plan:
                days_addition = days_addition_map[line.mon_plan]
                week_day = 0
                line.get_updation_data_delivery(days_addition=days_addition,
                                            week_day=week_day,
                                            from_date=from_date,
                                            to_date=to_date)

            if line.tue_plan:
                days_addition = days_addition_map[line.tue_plan]
                week_day = 1
                line.get_updation_data_delivery(days_addition=days_addition,
                                                week_day=week_day,
                                                from_date=from_date,
                                                to_date=to_date)

            if line.wed_plan:
                days_addition = days_addition_map[line.wed_plan]
                week_day = 2
                line.get_updation_data_delivery(days_addition=days_addition,
                                                week_day=week_day,
                                                from_date=from_date,
                                                to_date=to_date)

            if line.thu_plan:
                days_addition = days_addition_map[line.thu_plan]
                week_day = 3
                line.get_updation_data_delivery(days_addition=days_addition,
                                                week_day=week_day,
                                                from_date=from_date,
                                                to_date=to_date)

            if line.fri_plan:
                days_addition = days_addition_map[line.fri_plan]
                week_day = 4
                line.get_updation_data_delivery(days_addition=days_addition,
                                                week_day=week_day,
                                                from_date=from_date,
                                                to_date=to_date)

            if line.sat_plan:
                days_addition = days_addition_map[line.sat_plan]
                week_day = 5
                line.get_updation_data_delivery(days_addition=days_addition,
                                                week_day=week_day,
                                                from_date=from_date,
                                                to_date=to_date)

            if line.sun_plan:
                days_addition = days_addition_map[line.sun_plan]
                week_day = 6
                line.get_updation_data_delivery(days_addition=days_addition,
                                                week_day=week_day,
                                                from_date=from_date,
                                                to_date=to_date)



            #Visits

            if line.mon_visit_plan:
                days_addition = days_addition_map[line.mon_visit_plan]
                week_day = 0
                line.get_updation_data_visit(days_addition=days_addition,
                                            week_day=week_day,
                                            from_date=from_date,
                                            to_date=to_date)

            if line.tue_visit_plan:
                days_addition = days_addition_map[line.tue_visit_plan]
                week_day = 1
                line.get_updation_data_visit(days_addition=days_addition,
                                                week_day=week_day,
                                                from_date=from_date,
                                                to_date=to_date)

            if line.wed_visit_plan:
                days_addition = days_addition_map[line.wed_visit_plan]
                week_day = 2
                line.get_updation_data_visit(days_addition=days_addition,
                                                week_day=week_day,
                                                from_date=from_date,
                                                to_date=to_date)

            if line.thu_visit_plan:
                days_addition = days_addition_map[line.thu_visit_plan]
                week_day = 3
                line.get_updation_data_visit(days_addition=days_addition,
                                                week_day=week_day,
                                                from_date=from_date,
                                                to_date=to_date)

            if line.fri_visit_plan:
                days_addition = days_addition_map[line.fri_visit_plan]
                week_day = 4
                line.get_updation_data_visit(days_addition=days_addition,
                                                week_day=week_day,
                                                from_date=from_date,
                                                to_date=to_date)

            if line.sat_visit_plan:
                days_addition = days_addition_map[line.sat_visit_plan]
                week_day = 5
                line.get_updation_data_visit(days_addition=days_addition,
                                                week_day=week_day,
                                                from_date=from_date,
                                                to_date=to_date)

            if line.sun_visit_plan:
                days_addition = days_addition_map[line.sun_visit_plan]
                week_day = 6
                line.get_updation_data_visit(days_addition=days_addition,
                                                week_day=week_day,
                                                from_date=from_date,
                                                to_date=to_date)


    def get_updation_data_delivery(self, days_addition, week_day, from_date, to_date):
        start_date = from_date
        end_date = to_date
        for line in self:
            loop_date = self.get_next_weekdate(start_date, week_day)
            while loop_date <= end_date:
                self.env['sry.coverage.plan'].create({
                    'outlet_id': line.outlet_id.id,
                    'date': loop_date,
                    'coverage_id': line.coverage_id.id,
                    'cover_line_id':line.id,
                    'type' : 'delivery',
                    'plan_of' : line.coverage_id.plan_of
                    })
                loop_date = loop_date + timedelta(days=days_addition)


    def get_updation_data_visit(self, days_addition, week_day, from_date, to_date):
        start_date = from_date
        end_date = to_date
        for line in self:

            incrementing_days = days_addition

            loop_date = self.get_next_weekdate(start_date, week_day)
            while loop_date <= end_date:

                #check there is any delivery on the same day
                delivery = self.env['sry.coverage.plan'].search([('outlet_id', '=', line.outlet_id.id),
                                                                 ('date', '=', loop_date),
                                                                 ('cover_line_id', '=', line.id),
                                                                 ('type', '=', 'delivery'),
                                                                 ])

                if not delivery:
                    self.env['sry.coverage.plan'].create({
                        'outlet_id': line.outlet_id.id,
                        'date': loop_date,
                        'coverage_id': line.coverage_id.id,
                        'cover_line_id':line.id,
                        'type': 'visit',
                        'plan_of': line.coverage_id.plan_of
                        })

                if days_addition == 30:
                    #Find remaning number of days in the current month

                    # Get the last day of the current month
                    current_month_last_day = date(loop_date.year, loop_date.month, 1) + timedelta(days=32)
                    current_month_last_day = current_month_last_day.replace(day=1) - timedelta(days=1)

                    # Calculate the number of remaining days in October
                    remaining_days = (current_month_last_day - loop_date).days
                    incrementing_days = remaining_days + 1

                loop_date = loop_date + timedelta(days=incrementing_days)
                loop_date = self.get_next_date(loop_date, week_day)


    def get_next_date(self, loop_date, const):
        days_ahead = (const - loop_date.weekday() + 7) % 7
        next_week_date = loop_date + timedelta(days=days_ahead)
        return next_week_date

    def get_next_weekdate(self, loop_date, const):
        days_ahead = const - loop_date.weekday() + 7
        next_week_date = loop_date + timedelta(days=days_ahead)
        return next_week_date