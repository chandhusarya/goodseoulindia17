# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict
from operator import itemgetter
from markupsafe import Markup

from odoo import conf, http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.tools import groupby as groupbyelem

from odoo.osv.expression import OR

from odoo.addons.web.controllers.main import HomeStaticTemplateHelpers

import calendar as cal

from dateutil.relativedelta import relativedelta
from babel.dates import format_datetime, format_date
from odoo.tools.misc import get_lang

from datetime import date, datetime


class MerchandiserSchedule(CustomerPortal):

    @http.route(['/my/merchandiser_schedule_search'], type="json", auth="public", website=True)
    def merchandiser_search(self, outlet_name=None, merchandiser_name=None, display_type=None,
                            merch_or_saleperson = None, key_account_executive_name = None, **kwargs):
        data = self.generate_delivery_plan(outlet_name=outlet_name, merchandiser_name=merchandiser_name,
                                           display_type=display_type, merch_or_saleperson = merch_or_saleperson,
                                           key_account_executive_name= key_account_executive_name)
        return request.env.ref('sry_outlet_coverage_plan.merchandiser_schedule_calendar')._render(data)


    @http.route('/my/merchandiser_schedule', type='http', auth="user", website=True)
    def merchandiser_schedule(self, outlet_name=None, merchandiser_name=None, display_type=None, merch_or_saleperson = None,
                              key_account_executive_name = None, **kw):

        if not display_type:
            display_type = 'visit_deliveries'

        if not merch_or_saleperson:
            merch_or_saleperson = 'merch'

        data = self.generate_delivery_plan(outlet_name=outlet_name, merchandiser_name=merchandiser_name,
                                           display_type=display_type, merch_or_saleperson = merch_or_saleperson)
        return request.render("sry_outlet_coverage_plan.portal_calender_merchandiser_schedule", data)


    def generate_delivery_plan(self, outlet_name=None, merchandiser_name=None, display_type=None,
                               merch_or_saleperson = None, key_account_executive_name=None):

        formated_days = self.formated_weekdays(get_lang(request.env).code)


        # Display details on front end
        display_type_mapping = {'visit_only': 'Visit Only',
                                'visit_deliveries': 'Visit and Deliveries',
                                'deliveries_only': 'Deliveries Only'}

        display_type_name = display_type_mapping.get(display_type, '')

        # Need to know logged user is manager
        # Check is logged user is mapped in  account_excutive_id or account_manager_id or merchandiser_supervisor_id
        is_manager = False
        is_key_account_manager = False
        can_view_my_visit = merch_or_saleperson == 'sale' and True or False


        if merch_or_saleperson == 'merch':

            account_excutive = request.env['res.partner'].sudo().search_count(
                [('account_excutive_id', '=', request.env.uid)])
            if account_excutive > 0.01:
                is_manager = True
                can_view_my_visit = True

            if not is_manager:
                account_manager = request.env['res.partner'].sudo().search_count(
                    [('account_manager_id', '=', request.env.uid)])
                if account_manager > 0.01:
                    is_manager = True
                    is_key_account_manager = True

            if not is_manager:
                merchandiser_supervisor = request.env['res.partner'].sudo().search_count(
                    [('merchandiser_supervisor_id', '=', request.env.uid)])
                if merchandiser_supervisor > 0.01:
                    is_manager = True

        elif merch_or_saleperson == 'key_account_executive':
            is_manager = True
            is_key_account_manager = True


        show_merch_search = False
        show_account_executive_search = False
        if is_manager:
            show_merch_search = True
        if merch_or_saleperson == 'key_account_executive':
            show_merch_search = False
            show_account_executive_search = True
        if merch_or_saleperson == 'sale':
            show_merch_search = False



        domain = []
        if outlet_name:
            domain = [('short_name_merchandiser', 'ilike', outlet_name)]
        if merchandiser_name:
            merchandiser = request.env['res.users'].sudo().search([('name', 'ilike', merchandiser_name)]).ids
            if merchandiser:
                domain.append(('merchandiser_id2', 'in', merchandiser))

            else:
                #Return empty if merchandiser not found
                return {'slots': [],
                        'formated_days': formated_days,
                        'is_manager': True,
                        'display_type': display_type,
                        'display_type_name': display_type_name,
                        'merch_or_saleperson' : 'merch',
                        'is_key_account_manager' : is_key_account_manager,
                        'show_merch_search' : show_merch_search,
                        'show_account_executive_search' : show_account_executive_search
                        }

        if merch_or_saleperson == 'sale':
            domain.append(('account_excutive_id', '=', request.env.uid))


        if merch_or_saleperson == 'key_account_executive':

            if key_account_executive_name:

                key_account_executive = request.env['res.users'].sudo().search(
                    [('name', 'ilike', key_account_executive_name)]).ids
                if key_account_executive:
                    domain.append(('account_excutive_id', 'in', key_account_executive))

                else:
                    # Return empty if key account executive not found
                    return {'slots': [],
                            'formated_days': formated_days,
                            'is_manager': True,
                            'display_type': display_type,
                            'display_type_name': display_type_name,
                            'merch_or_saleperson': 'merch',
                            'is_key_account_manager': is_key_account_manager,
                            'show_merch_search': show_merch_search,
                            'show_account_executive_search': show_account_executive_search
                            }
            else:
                domain.append(('account_manager_id', '=', request.env.uid))

        if not merchandiser_name and merch_or_saleperson == 'merch':
            domain = domain + ['|', '|', '|', ('merchandiser_id2', '=', request.env.uid),
                  ('account_excutive_id', '=', request.env.uid),
                  ('account_manager_id', '=', request.env.uid),
                  ('merchandiser_supervisor_id', '=', request.env.uid)]

        delivery_outlets = request.env['res.partner'].sudo().search(domain).ids







        today = datetime.now()
        start = today
        month_dates_calendar = cal.Calendar(0).monthdatescalendar
        last_day = today + relativedelta(days=30)
        max_day_in_month = cal.monthrange(last_day.year, last_day.month)[1]
        last_day = last_day.replace(day=max_day_in_month)

        months = []

        plan_mapped = {}
        if display_type in ['deliveries_only', 'visit_deliveries']:

            if merch_or_saleperson in ['sale', 'key_account_executive']:
                plans = request.env['sry.coverage.plan'].sudo().search(
                    [('date', '>=', start + relativedelta(days=-30)),
                     ('date', '<=', last_day),
                     ('outlet_id', 'in', delivery_outlets),
                     ('type', '=', 'delivery'),
                     ('plan_of', '=', 'executive')])

            else:
                plans = request.env['sry.coverage.plan'].sudo().search(
                    [('date', '>=', start + relativedelta(days=-30)),
                     ('date', '<=', last_day),
                     ('outlet_id', 'in', delivery_outlets),
                     ('type', '=', 'delivery'),
                     ('plan_of', '=', 'merchandiser')])

            for each_plan in plans:
                key = each_plan.date
                if key in plan_mapped:

                    if is_manager:
                        plan_mapped[key]['Delivery'].append(each_plan.outlet_id)
                    else:
                        plan_mapped[key]['Delivery'].append(each_plan.outlet_id.short_name_merchandiser or each_plan.outlet_id.name)
                else:

                    if is_manager:
                        plan_mapped[key] = {'Delivery' : [each_plan.outlet_id],
                                            'Visit' : []}
                    else:
                        plan_mapped[key] = {'Delivery' : [each_plan.outlet_id.short_name_merchandiser or each_plan.outlet_id.name],
                                            'Visit' : []}


        if display_type in ['visit_only', 'visit_deliveries']:

            plans = []

            if merch_or_saleperson in ['sale', 'key_account_executive']:

                plans = request.env['sry.coverage.plan'].sudo().search(
                    [('date', '>=', start + relativedelta(days=-30)),
                     ('date', '<=', last_day),
                     ('outlet_id', 'in', delivery_outlets),
                     ('type', '=', 'visit'),
                     ('plan_of', '=', 'executive')])

            else:

                plans = request.env['sry.coverage.plan'].sudo().search(
                    [('date', '>=', start + relativedelta(days=-30)),
                     ('date', '<=', last_day),
                     ('outlet_id', 'in', delivery_outlets),
                     ('type', '=', 'visit'),
                     ('plan_of', '=', 'merchandiser')])


            for each_plan in plans:
                key = each_plan.date
                if key in plan_mapped:
                    if is_manager:
                        plan_mapped[key]['Visit'].append(each_plan.outlet_id)
                    else:
                        plan_mapped[key]['Visit'].append(
                            each_plan.outlet_id.short_name_merchandiser or each_plan.outlet_id.name)
                else:
                    if is_manager:
                        plan_mapped[key] = {'Visit' : [each_plan.outlet_id],
                                            'Delivery' : []}
                    else:
                        plan_mapped[key]= {'Visit' : [each_plan.outlet_id.short_name_merchandiser or each_plan.outlet_id.name],
                                           'Delivery' : []}

        while (start.year, start.month) <= (last_day.year, last_day.month):
            dates = month_dates_calendar(start.year, start.month)
            for week_index, week in enumerate(dates):
                for day_index, day in enumerate(week):
                    mute_cls = weekend_cls = today_cls = None
                    if day.weekday() == cal.SUNDAY:
                        weekend_cls = 'o_weekend'
                    if day == today.date() and day.month == today.month:
                        today_cls = 'o_today'


                    #If logger user is manager we need to group data by accounts manager
                    if is_manager:
                        if day in plan_mapped:
                            merchandiser_wise = {}
                            all_outlets = plan_mapped[day]

                            #Deliveries
                            for outlet in all_outlets['Delivery']:

                                merchandiser_name = outlet.merchandiser_id2 and outlet.merchandiser_id2.name or "Merch Not Assigned"
                                if merch_or_saleperson == 'key_account_executive':
                                    merchandiser_name = outlet.account_excutive_id and outlet.account_excutive_id.name or "Executive Not Assigned"

                                if merchandiser_name in merchandiser_wise:
                                    merchandiser_wise[merchandiser_name]['Delivery'].append(outlet.short_name_merchandiser or outlet.name)
                                else:
                                    merchandiser_wise[merchandiser_name] = {'Delivery' : [ outlet.short_name_merchandiser or outlet.name],
                                                                            'Visit' : []}


                            #Visists
                            for outlet in all_outlets['Visit']:

                                merchandiser_name = outlet.merchandiser_id2 and outlet.merchandiser_id2.name or "Merch Not Assigned"
                                if merch_or_saleperson == 'key_account_executive':
                                    merchandiser_name = outlet.account_excutive_id and outlet.account_excutive_id.name or "Executive Not Assigned"

                                if merchandiser_name in merchandiser_wise:
                                    merchandiser_wise[merchandiser_name]['Visit'].append(outlet.short_name_merchandiser or outlet.name)
                                else:
                                    merchandiser_wise[merchandiser_name] = {'Visit' : [ outlet.short_name_merchandiser or outlet.name],
                                                                            'Delivery' : []}


                            outlets = merchandiser_wise


                        else:
                            outlets = None


                    else:
                        if day in plan_mapped:
                            outlets = plan_mapped[day]
                        else:
                            outlets = None

                    dates[week_index][day_index] = {
                        'day': day,
                        'weekend_cls': weekend_cls,
                        'today_cls': today_cls,
                        'mute_cls': mute_cls,
                        'outlets': outlets,
                        'is_manager': is_manager,
                    }

            months.append({
                'id': len(months),
                'month': format_datetime(start, 'MMMM Y', locale=get_lang(request.env).code),
                'weeks': dates,
            })
            start = start + relativedelta(months=1)



        #Display data of who

        display_data_of = "Merchandisers"
        if merch_or_saleperson == 'sale':
            display_data_of = "My Visits"
        elif merch_or_saleperson == 'key_account_executive':
            display_data_of = "Key Account Executives"



        return {'slots': months,
                'formated_days': formated_days,
                'is_manager': is_manager,
                'display_type' : display_type,
                'display_type_name' : display_type_name,
                'can_view_my_visit' : can_view_my_visit,
                'display_data_of' : display_data_of,
                'merch_or_saleperson' : merch_or_saleperson,
                'is_key_account_manager' : is_key_account_manager,
                'show_merch_search' : show_merch_search,
                'show_account_executive_search' : show_account_executive_search
                }








    def formated_weekdays(self, locale):
        """ Return the weekdays' name for the current locale
            from Mon to Sun.
            :param locale: locale
        """
        formated_days = [
            format_date(date(2021, 3, day), 'EEE', locale=locale)
            for day in range(1, 8)
        ]
        return formated_days