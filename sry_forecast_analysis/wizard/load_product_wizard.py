import math
from odoo.exceptions import ValidationError, AccessError, UserError
from odoo import models, fields, api,_
from datetime import datetime,timedelta, date
from dateutil.relativedelta import relativedelta

class sry_product_load_wizard(models.TransientModel):
    _name = 'sry.product.load.wizard'

    product_ids = fields.Many2many('product.product', string='Product', domain=[('detailed_type','=','product')])
    compare_range = fields.Integer(string="No of Month(s)", default=4)

    def _get_preceding_months(self,start_date):
        period_list = []
        for i in range(self.compare_range):
            month_delta = start_date.month - i - 1
            year_delta = start_date.year

            if month_delta < 0:
                month_delta += 12
                year_delta -= 1

            target_date = datetime(year_delta, month_delta + 1, 1)

            formatted_date = target_date.strftime('%Y-%m')
            period_list.append(formatted_date)
        return period_list

    def button_list_view(self):
        return {
            'name': 'Sales Forecast Analysis',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,pivot',
            'view_type': 'form',
            'res_model': 'sry.forecast.analysis',
            'domain': self._get_domain(),
            'view_id': False,
            'target': 'self'
        }

    def _get_domain(self):
        if not self.product_ids:
            raise ValidationError(_('No products selected'))
        product_list = [product.id for product in self.product_ids]
        domain = [('product_id', 'in', product_list)]
        current_date = datetime.now()
        period_list = self._get_preceding_months(current_date)
        period_list += self._get_preceding_months(current_date - relativedelta(years=1))
        if period_list:
            domain += [('period', 'in', period_list)]
        return domain

    def button_generate_xlsx(self):
        if not 1 <= self.compare_range <= 12:
            raise ValidationError(_("Invalid Number of Months"))

        month_full_name = [self._get_month_full_name(col) for col in range(self.compare_range - 1,-1, -1)]
        month_short_name = [self._get_month_short_name(col) for col in range(self.compare_range - 1,-1, -1)]

        domain = self._get_domain()
        analysis_records = self.env['sry.forecast.analysis'].search(domain)
        location_wise_stocks = self._get_location_wise_stocks()
        wh_locations = self.env['sry.forecast.location'].search([('total', '=', False)]).filtered(lambda l:l.report == 'forecast').sorted('name').mapped('name')
        product_total_stock_onhand = self._get_stock_totals_product()

        #cha commented
        #purchase_records =self._get_purchase_records()

        picking_records =self._get_picking_records()
        blanket_order_data = self.get_blanket_order_data()


        next_3months_budget_avgs_records = self._get_next_3months_budget_avgs_records()
        rows = []
        max_number_of_eta = 0
        for product in self.product_ids:

            product_etas, unformated_eta = self._get_product_eta(product.id)
            if len(product_etas) > max_number_of_eta:
                max_number_of_eta = len(product_etas)

            cols = {}
            cols.update({'brand': product.brand.name})
            cols.update({'category': product.categ_id.name})
            cols.update({'item_code': product.default_code})
            cols.update({'item_name': product.name})
            first_shipment_date = self._get_first_shipment_date(product.id, picking_records)
            cols.update({'first_shipment_date': first_shipment_date})
            pcb = product.packaging_ids.sorted('qty', reverse=True)[:1]
            cols.update({'pcb': pcb.qty})
            uom = product.packaging_ids.sorted('qty')[:1]
            cols.update({'uom': uom.name})
            cols.update({'shelf_life': product.ps_shelf_life or ""})
            self.initialize_cols_lists(cols)
            cummulative_total_curryear_actual_total = 0
            cummulative_regular_curryear_actual_export = 0
            cummulative_regular_curryear_actual_total = 0
            cummulative_regular_curryear_actual_foodservice = 0
            cummulative_regular_curryear_actual_retail = 0
            cummulative_regular_curryear_actual_wholesale = 0
            cummulative_total_prevyear_actual_total = 0
            prev_average_actual_curryr = 0
            prev_average_actual_prevyr = 0
            for col in range(self.compare_range, 0, -1):
                cols["nearexp_prevyear"].append(self._get_nearexp_prevyear(product.id, analysis_records, col))
                cols["nearexp_curryear"].append(self._get_nearexp_curryear(product.id, analysis_records, col))
                cols["nearexp_yroveryr_qty"].append(self._get_nearexp_yroveryr_qty(product.id, analysis_records,col))
                cols["nearexp_yroveryr_perc"].append(self._get_nearexp_yroveryr_perc(product.id, analysis_records,col))
                cols["promo_prevyear_budg_total"].append(self._get_promo_prevyear_budg_total(product.id, analysis_records,col))
                cols["promo_prevyear_actual_priceoff"].append(self._get_promo_prevyear_actual_priceoff(product.id, analysis_records,col))
                cols["promo_prevyear_actual_pricecomp"].append(self._get_promo_prevyear_actual_pricecomp(product.id, analysis_records,col))
                cols["promo_prevyear_actual_total"].append(self._get_promo_prevyear_actual_total(product.id, analysis_records,col))
                cols["promo_prevyear_variance_qty"].append(self._get_promo_prevyear_variance_qty(product.id, analysis_records,col))
                cols["promo_prevyear_variance_perc"].append(self._get_promo_prevyear_variance_perc(product.id, analysis_records,col))
                cols["promo_curryear_budg_total"].append(self._get_promo_curryear_budg_total(product.id, analysis_records,col))
                cols["promo_curryear_actual_priceoff"].append(self._get_promo_curryear_actual_priceoff(product.id, analysis_records,col))
                cols["promo_curryear_actual_pricecomp"].append(self._get_promo_curryear_actual_pricecomp(product.id, analysis_records,col))
                cols["promo_curryear_actual_total"].append(self._get_promo_curryear_actual_total(product.id, analysis_records,col))
                cols["promo_curryear_variance_qty"].append(self._get_promo_curryear_variance_qty(product.id, analysis_records,col))
                cols["promo_curryear_variance_perc"].append(self._get_promo_curryear_variance_perc(product.id, analysis_records,col))
                cols["promo_yroveryr_budg_qty"].append(self._get_promo_yroveryr_budg_qty(product.id, analysis_records,col))
                cols["promo_yroveryr_budg_perc"].append(self._get_promo_yroveryr_budg_perc(product.id, analysis_records,col))
                cols["promo_yroveryr_actual_qty"].append(self._get_promo_yroveryr_actual_qty(product.id, analysis_records,col))
                cols["promo_yroveryr_actual_perc"].append(self._get_promo_yroveryr_actual_perc(product.id, analysis_records,col))
                cols["regular_prevyear_budg_export"].append(self._get_regular_prevyear_budg_export(product.id, analysis_records,col))
                cols["regular_prevyear_budg_foodservice"].append(self._get_regular_prevyear_budg_foodservice(product.id, analysis_records,col))
                cols["regular_prevyear_budg_retail"].append(self._get_regular_prevyear_budg_retail(product.id, analysis_records,col))
                cols["regular_prevyear_budg_wholesale"].append(self._get_regular_prevyear_budg_wholesale(product.id, analysis_records,col))
                cols["regular_prevyear_budg_total"].append(self._get_regular_prevyear_budg_total(product.id, analysis_records,col))
                cols["regular_prevyear_actual_export"].append(self._get_regular_prevyear_actual_export(product.id, analysis_records,col))
                cols["regular_prevyear_actual_foodservice"].append(self._get_regular_prevyear_actual_foodservice(product.id, analysis_records,col))
                cols["regular_prevyear_actual_retail"].append(self._get_regular_prevyear_actual_retail(product.id, analysis_records,col))
                cols["regular_prevyear_actual_wholesale"].append(self._get_regular_prevyear_actual_wholesale(product.id, analysis_records,col))
                cols["regular_prevyear_actual_total"].append(self._get_regular_prevyear_actual_total(product.id, analysis_records,col))
                cols["regular_prevyear_variance_qty"].append(self._get_regular_prevyear_variance_qty(product.id, analysis_records,col))
                cols["regular_prevyear_variance_perc"].append(self._get_regular_prevyear_variance_perc(product.id, analysis_records,col))
                cols["regular_curryear_budg_export"].append(self._get_regular_curryear_budg_export(product.id, analysis_records,col))
                cols["regular_curryear_budg_foodservice"].append(self._get_regular_curryear_budg_foodservice(product.id, analysis_records,col))
                cols["regular_curryear_budg_retail"].append(self._get_regular_curryear_budg_retail(product.id, analysis_records,col))
                cols["regular_curryear_budg_wholesale"].append(self._get_regular_curryear_budg_wholesale(product.id, analysis_records,col))
                cols["regular_curryear_budg_total"].append(self._get_regular_curryear_budg_total(product.id, analysis_records,col))

                regular_curryear_actual_export = self._get_regular_curryear_actual_export(product.id, analysis_records,col)
                cummulative_regular_curryear_actual_export += regular_curryear_actual_export
                cols["regular_curryear_actual_export"].append(round(regular_curryear_actual_export,1))

                regular_curryear_actual_foodservice = self._get_regular_curryear_actual_foodservice(product.id, analysis_records,col)
                cummulative_regular_curryear_actual_foodservice += regular_curryear_actual_foodservice
                cols["regular_curryear_actual_foodservice"].append(round(regular_curryear_actual_foodservice,1))

                regular_curryear_actual_retail = self._get_regular_curryear_actual_retail(product.id, analysis_records,col)
                cummulative_regular_curryear_actual_retail += regular_curryear_actual_retail
                cols["regular_curryear_actual_retail"].append(round(regular_curryear_actual_retail,1))

                regular_curryear_actual_wholesale = self._get_regular_curryear_actual_wholesale(product.id, analysis_records,col)
                cummulative_regular_curryear_actual_wholesale += regular_curryear_actual_wholesale
                cols["regular_curryear_actual_wholesale"].append(round(regular_curryear_actual_wholesale,1))

                regular_curryear_actual_total = self._get_regular_curryear_actual_total(product.id, analysis_records, col)
                cummulative_regular_curryear_actual_total +=regular_curryear_actual_total
                cols["regular_curryear_actual_total"].append(round(regular_curryear_actual_total,1))
                cols["regular_curryear_variance_qty"].append(self._get_regular_curryear_variance_qty(product.id, analysis_records,col))
                cols["regular_curryear_variance_perc"].append(self._get_regular_curryear_variance_perc(product.id, analysis_records,col))
                cols["regular_yroveryr_budget_qty"].append(self._get_regular_yroveryr_budget_qty(product.id, analysis_records,col))
                cols["regular_yroveryr_budget_perc"].append(self._get_regular_yroveryr_budget_perc(product.id, analysis_records,col))
                cols["regular_yroveryr_actual_qty"].append(self._get_regular_yroveryr_actual_qty(product.id, analysis_records,col))
                cols["regular_yroveryr_actual_perc"].append(self._get_regular_yroveryr_actual_perc(product.id, analysis_records,col))
                cols["total_prevyear_budg_total"].append(self._get_total_prevyear_budg_total(product.id, analysis_records,col))

                total_prevyear_actual_total = self._get_total_prevyear_actual_total(product.id, analysis_records,col)
                if col == 1 and cummulative_total_prevyear_actual_total:
                    prev_average_actual_prevyr = cummulative_total_prevyear_actual_total / (self.compare_range - 1)
                cummulative_total_prevyear_actual_total += total_prevyear_actual_total

                cols["total_prevyear_actual_total"].append(round(total_prevyear_actual_total,1))
                cols["total_prevyear_variance_quantity"].append(self._get_total_prevyear_variance_quantity(product.id, analysis_records,col))
                cols["total_prevyear_variance_perc"].append(self._get_total_prevyear_variance_perc(product.id, analysis_records,col))
                cols["total_curryear_budg_total"].append(self._get_total_curryear_budg_total(product.id, analysis_records,col))

                total_curryear_actual_total = self._get_total_curryear_actual_total(product.id, analysis_records, col)
                if col == 1 and cummulative_total_curryear_actual_total:
                    prev_average_actual_curryr = cummulative_total_curryear_actual_total / (self.compare_range - 1)
                cummulative_total_curryear_actual_total += total_curryear_actual_total

                cols["total_curryear_actual_total"].append(round(total_curryear_actual_total,1))
                cols["total_curryear_variance_quantity"].append(self._get_total_curryear_variance_quantity(product.id, analysis_records,col))
                cols["total_curryear_variance_perc"].append(self._get_total_curryear_variance_perc(product.id, analysis_records,col))
                cols["total_yroveryr_budg_quantity"].append(self._get_total_yroveryr_budg_quantity(product.id, analysis_records,col))
                cols["total_yroveryr_budg_perc"].append(self._get_total_yroveryr_budg_perc(product.id, analysis_records,col))
                cols["total_yroveryr_actual_quantity"].append(self._get_total_yroveryr_actual_quantity(product.id, analysis_records,col))
                cols["total_yroveryr_actual_perc"].append(self._get_total_yroveryr_actual_perc(product.id, analysis_records,col))
            cols.update({'prev_average_actual_curryr': round(prev_average_actual_curryr,1)})
            cols.update({'prev_average_actual_prevyr': round(prev_average_actual_prevyr,1)})
            next_average_budget = self._get_next_average_budget(product.id, next_3months_budget_avgs_records)
            cols.update({'next_average_budget': round(next_average_budget,1)})
            eom_forecast = self._get_eom_forecast(product.id, analysis_records, col)
            cols.update({'eom_forecast': eom_forecast})
            cols.update({'trend': self._get_trend(first_shipment_date, prev_average_actual_curryr, eom_forecast)})
            cols.update({'wh_locations': wh_locations})
            cols.update({'location_wise_stocks': [entry for entry in location_wise_stocks if entry['product_id'] == product.id]})

            total_stock_onhand =  self._get_total_stock_onhand(product.id, product_total_stock_onhand)
            cols.update({'total_stock_onhand': total_stock_onhand})

            average_sales_month = (prev_average_actual_curryr + eom_forecast) / 2
            cols.update({'average_sales_month': round(average_sales_month,1)})

            soh_coverage_month = round(average_sales_month and total_stock_onhand / average_sales_month or 0, 1)
            cols.update({'soh_coverage_month': soh_coverage_month})

            soh_coverage_days = round(soh_coverage_month * 30)
            cols.update({'soh_coverage_days': soh_coverage_days})

            ordering_lead_time = product.seller_ids.name.delivery_lead_time
            cols.update({'ordering_lead_time': ordering_lead_time})

            #Cha change
            #if eta is available, system will consider first eta. Other wise leade time is taken
            no_stock_days_before_shipment, days_to_arrive = self.get_no_stock_days_before_shipment(soh_coverage_days, ordering_lead_time, unformated_eta)

            #no_stock_days_before_shipment is comes are negative. if item still in stock when considering eta or lead time, that items no need to
            #show in the report
            no_stock_days_before_shipment_corrected = no_stock_days_before_shipment * -1
            if no_stock_days_before_shipment_corrected < 0:
                no_stock_days_before_shipment_corrected = 0
            cols.update({'no_stock_days_before_shipment': no_stock_days_before_shipment_corrected})

            # Cha commented
            #soh_bal_before_shipment = total_stock_onhand - (average_sales_month * (ordering_lead_time / 30))
            soh_bal_before_shipment = total_stock_onhand - (average_sales_month * (days_to_arrive / 30))
            soh_bal_before_shipment_corrected = 0
            #If there is any actual stock balance then only that stock should show. Other wise no need to show negative stock
            if soh_bal_before_shipment > 0:
                soh_bal_before_shipment_corrected = soh_bal_before_shipment
            cols.update({'soh_bal_before_shipment': round(soh_bal_before_shipment_corrected, 1)})

            soh_coverage_before_shipment = average_sales_month and soh_bal_before_shipment_corrected / average_sales_month or 0
            cols.update({'soh_coverage_before_shipment': round(soh_coverage_before_shipment,1)})

            order_required = self._get_order_required(eom_forecast, total_stock_onhand, soh_coverage_month)
            cols.update({'order_required': order_required})

            cols.update({'minimum_order_qty': ''})

            safety_stock = max(prev_average_actual_curryr, eom_forecast) * (ordering_lead_time / 30)
            cols.update({'safety_stock':round(safety_stock,1)})

            lead_time_demand = ((eom_forecast + prev_average_actual_curryr)/2) * (ordering_lead_time / 30)
            cols.update({'lead_time_demand': round(lead_time_demand,1)})

            forecasted_qty_to_order = self._get_forecasted_qty_to_order(order_required, soh_bal_before_shipment, lead_time_demand)
            cols.update({'forecasted_qty_to_order': round(forecasted_qty_to_order,1)})

            inventory_forecast_qty_export = cummulative_regular_curryear_actual_total and (cummulative_regular_curryear_actual_export/cummulative_regular_curryear_actual_total) * forecasted_qty_to_order or 0
            cols.update({'inventory_forecast_qty_export': round(inventory_forecast_qty_export,1)})

            inventory_forecast_qty_foodservice = cummulative_regular_curryear_actual_total and (cummulative_regular_curryear_actual_foodservice/cummulative_regular_curryear_actual_total) * forecasted_qty_to_order or 0
            cols.update({'inventory_forecast_qty_foodservice': round(inventory_forecast_qty_foodservice,1)})

            inventory_forecast_qty_retail = cummulative_regular_curryear_actual_total and (cummulative_regular_curryear_actual_retail/cummulative_regular_curryear_actual_total) * forecasted_qty_to_order or 0
            cols.update({'inventory_forecast_qty_retail': round(inventory_forecast_qty_retail,1)})

            inventory_forecast_qty_wholesale = cummulative_regular_curryear_actual_total and (cummulative_regular_curryear_actual_wholesale/cummulative_regular_curryear_actual_total) * forecasted_qty_to_order or 0
            cols.update({'inventory_forecast_qty_wholesale': round(inventory_forecast_qty_wholesale,1)})

            inventory_forecast_qty_total = inventory_forecast_qty_export + inventory_forecast_qty_foodservice + inventory_forecast_qty_retail + inventory_forecast_qty_wholesale
            cols.update({'inventory_forecast_qty_total': round(inventory_forecast_qty_total,1)})

            #Cha Update
            #cols.update({'pending_balance_qty_from_supplier': self._get_pending_balance_qty_from_supplier(product.id,purchase_records)})
            cols.update({'pending_qty_eta': product_etas})

            cols.update({'remaining_qty_blanket_order': self.find_blanket_order_qty(blanket_order_data, product.id)})

            rows.append(cols)

        return self.env.ref('sry_forecast_analysis.report_forecast').report_action(self, data={
            'cols': self.compare_range,
            'rows': rows,
            'max_number_of_eta' : max_number_of_eta,
            'month_full': month_full_name,
            'month_short': month_short_name,
            'wh_locations': wh_locations,
        })

    def get_no_stock_days_before_shipment(self, soh_coverage_days, ordering_lead_time, product_etas):
        # if eta is avaibale, it will be computed from nearest eta. Other wise lead time is considered
        if not product_etas:
            return math.ceil(soh_coverage_days - ordering_lead_time), ordering_lead_time
        else:
            eta_dict = product_etas[0]
            eta = eta_dict['eta']

            delta = eta - date.today()
            days = math.ceil(soh_coverage_days - delta.days)

            return days, delta.days




    def find_blanket_order_qty(self, blanket_order_data, product_id):
        return blanket_order_data.get(product_id, 0)



    def get_blanket_order_data(self):

        result = {}
        requisition = self.env['purchase.requisition'].search([])
        for req in requisition:
            if req.state_blanket_order == 'ongoing':
                for line in req.line_ids:
                    product_packaging_qty = line.product_packaging_qty
                    pkg_qty_ordered = line.pkg_qty_ordered

                    remaining_qty = product_packaging_qty - pkg_qty_ordered
                    if remaining_qty > 0:
                        if line.product_id.id in result:
                            result[line.product_id.id] += remaining_qty
                        else:
                            result[line.product_id.id] = remaining_qty

        return result



    def _get_total_stock_onhand(self,product_id, product_total_stock_onhand):
        result = 0
        for entry in product_total_stock_onhand:
            if entry and entry['product_id'] == product_id:
                result = round(entry['onhand'],1)
        return result

    #cha update
    # def _get_pending_balance_qty_from_supplier(self,product_id, purchase_records):
    #     matching_record = next((record for record in purchase_records if record['product_id'] == product_id), None)
    #     result = round(matching_record['to_rcv'],1) if matching_record else ""
    #     return result

    def _get_product_eta(self, product_id):
        result = self.env['report.sry_forecast_analysis.stock_onhand_report']._get_etas(product_id)

        unformated_result = result.copy()

        final_result = []
        for r in result:
            eta = r['eta']
            eta = eta.strftime("%d-%m-%Y")
            final_result.append({
                'eta' : eta,
                'qty' : r['qty']
            })

        return final_result, unformated_result


    def _get_trend(self, first_shipment_date, prev_average_actual_curryr, eom_forecast):
        current_date = datetime.now()
        if not first_shipment_date:
            return ""
        first_shipment_date = datetime.strptime(first_shipment_date, '%Y-%m-%d')
        if first_shipment_date >= (current_date - timedelta(days=90)):
            result = "Filling the Pipeline"
        elif eom_forecast > prev_average_actual_curryr:
            result = "Upper Trend"
        else:
            result = "Lower Trend"
        return result

    def _get_order_required(self, eom_forecast, total_stock_onhand, soh_coverage_month):
        if eom_forecast == 0:
            result = "Check SKU Status" if total_stock_onhand < 5 else "Non Moving"
        else:
            result = "Yes" if soh_coverage_month < 3 else "No"
        return result

    def _get_first_shipment_date(self, product_id, picking_records):
        matching_record = next((record for record in picking_records if record['product_id'] == product_id), None)
        result = matching_record and matching_record['scheduled_date'] or ""
        return result

    def _get_forecasted_qty_to_order(self, order_required, soh_bal_before_shipment, lead_time_demand):
        result = 0
        if order_required == 'Yes':
            if soh_bal_before_shipment < 0:
                result = lead_time_demand
            else:
                result = lead_time_demand - soh_bal_before_shipment
        return result

    def _get_eom_forecast(self, product_id, analysis_records, col):
        total_curryear_actual_total = self._get_total_curryear_actual_total(product_id, analysis_records, col)
        current_date = datetime.today()
        if total_curryear_actual_total > 0:
            upto_day = current_date.day
            days_in_month = (current_date + relativedelta(day=31)).day
            result = round((total_curryear_actual_total / upto_day) * days_in_month,1)
        else:
            result = 0
        return result

    def _get_total_yroveryr_actual_perc(self, product_id, analysis_records, col):
        get_total_curryear_budg_total = self._get_total_prevyear_actual_total(product_id, analysis_records,col)
        if get_total_curryear_budg_total:
            result = round(self._get_total_yroveryr_actual_quantity(product_id, analysis_records,col) / abs(get_total_curryear_budg_total) * 100)
        else:
            result= 0
        return result

    def _get_total_yroveryr_actual_quantity(self, product_id, analysis_records, col):
        result = self._get_total_curryear_actual_total(product_id, analysis_records,col) - self._get_total_prevyear_actual_total(product_id, analysis_records,col)
        return result

    def _get_total_yroveryr_budg_perc(self, product_id, analysis_records, col):
        get_total_prevyear_budg_total = self._get_total_prevyear_budg_total(product_id, analysis_records,col)
        if get_total_prevyear_budg_total:
            result = round(self._get_total_yroveryr_budg_quantity(product_id, analysis_records,col) / abs(get_total_prevyear_budg_total) * 100)
        else:
            result= 0
        return result

    def _get_total_yroveryr_budg_quantity(self, product_id, analysis_records, col):
        result = self._get_total_curryear_budg_total(product_id, analysis_records,col) - self._get_total_prevyear_budg_total(product_id, analysis_records,col)
        return result

    def _get_total_curryear_variance_perc(self,product_id, analysis_records,col):
        get_total_curryear_budg_total = self._get_total_curryear_budg_total(product_id, analysis_records,col)
        if get_total_curryear_budg_total:
            result = round(self._get_total_curryear_variance_quantity(product_id, analysis_records,col) / abs(get_total_curryear_budg_total) * 100)
        else:
            result= 0
        return result

    def _get_total_curryear_variance_quantity(self,product_id, analysis_records,col):
        result = self._get_total_curryear_actual_total(product_id, analysis_records,col) - self._get_total_curryear_budg_total(product_id, analysis_records,col)
        return result

    def _get_total_curryear_actual_total(self,product_id, analysis_records,col):
        result = self._get_regular_curryear_actual_total(product_id, analysis_records,col) + self._get_promo_curryear_actual_total(product_id, analysis_records,col)
        return result

    def _get_total_curryear_budg_total(self,product_id, analysis_records,col):
        result = self._get_regular_curryear_budg_total(product_id,analysis_records,col)
        return result

    def _get_total_prevyear_variance_perc(self,product_id, analysis_records,col):
        get_total_prevyear_budg_total = self._get_total_prevyear_budg_total(product_id, analysis_records,col)
        if get_total_prevyear_budg_total:
            result = round(self._get_total_prevyear_variance_quantity(product_id, analysis_records,col) / abs(get_total_prevyear_budg_total) * 100)
        else:
            result= 0
        return result

    def _get_total_prevyear_variance_quantity(self,product_id, analysis_records,col):
        result = self._get_total_prevyear_actual_total(product_id, analysis_records,col) - self._get_total_prevyear_budg_total(product_id, analysis_records,col)
        return round(result,1)

    def _get_total_prevyear_actual_total(self,product_id, analysis_records,col):
        result = self._get_promo_prevyear_actual_total(product_id, analysis_records,col) + self._get_regular_prevyear_actual_total(product_id, analysis_records,col)
        return round(result,1)

    def _get_total_prevyear_budg_total(self,product_id, analysis_records,col):
        #Although, both regular budget and promotion budget having the total budget, here will be regular budget as advised by mullin. This cell is dependent for other cell
        result = self._get_regular_prevyear_budg_total(product_id, analysis_records,col)
        return round(result,1)

    def _get_regular_yroveryr_actual_perc(self,product_id, analysis_records,col):
        get_regular_prevyear_actual_total = self._get_regular_prevyear_actual_total(product_id, analysis_records,col)
        if get_regular_prevyear_actual_total:
            result = round(self._get_regular_yroveryr_actual_qty(product_id, analysis_records,col) / abs(get_regular_prevyear_actual_total) * 100)
        else:
            result= 0
        return result

    def _get_regular_yroveryr_actual_qty(self,product_id, analysis_records,col):
        result = self._get_regular_curryear_actual_total(product_id, analysis_records,col) - self._get_regular_prevyear_actual_total(product_id, analysis_records,col)
        return round(result,1)

    def _get_regular_yroveryr_budget_perc(self,product_id, analysis_records,col):
        get_regular_prevyear_budg_total = self._get_regular_prevyear_budg_total(product_id, analysis_records,col)
        if get_regular_prevyear_budg_total:
            result = round(self._get_regular_yroveryr_budget_qty(product_id, analysis_records,col) / abs(get_regular_prevyear_budg_total) * 100)
        else:
            result= 0
        return result

    def _get_regular_yroveryr_budget_qty(self,product_id, analysis_records,col):
        result = self._get_regular_curryear_budg_total(product_id, analysis_records,col) - self._get_regular_prevyear_budg_total(product_id, analysis_records,col)
        return round(result,1)

    def _get_regular_curryear_variance_perc(self,product_id, analysis_records,col):
        get_regular_curryear_budg_total = self._get_regular_curryear_budg_total(product_id, analysis_records,col)
        if get_regular_curryear_budg_total:
            result = round(self._get_regular_curryear_variance_qty(product_id, analysis_records,col) / abs(get_regular_curryear_budg_total) * 100)
        else:
            result= 0
        return result

    def _get_regular_curryear_variance_qty(self,product_id, analysis_records,col):
        result = self._get_regular_curryear_actual_total(product_id, analysis_records,col) - self._get_regular_curryear_budg_total(product_id, analysis_records,col)
        return round(result,1)

    def _get_regular_curryear_actual_total(self,product_id, analysis_records,col):
        result = self._get_regular_curryear_actual_export(product_id, analysis_records,col) + self._get_regular_curryear_actual_foodservice(product_id,analysis_records,col) \
                 + self._get_regular_curryear_actual_retail(product_id, analysis_records,col) + self._get_regular_curryear_actual_wholesale(product_id, analysis_records,col)
        return round(result,1)

    def _get_regular_curryear_actual_wholesale(self,product_id, analysis_records,col):
        period = self._get_curryr_period(col)
        curryr_rec = analysis_records.filtered(lambda l: l.period == period and l.product_id.id == product_id and l.trade_channel.id == 2)
        return round(curryr_rec.regular_sales,1)

    def _get_regular_curryear_actual_retail(self,product_id, analysis_records,col):
        period = self._get_curryr_period(col)
        curryr_rec = analysis_records.filtered(lambda l: l.period == period and l.product_id.id == product_id and l.trade_channel.id == 1)
        return round(curryr_rec.regular_sales,1)

    def _get_regular_curryear_actual_foodservice(self,product_id, analysis_records,col):
        period = self._get_curryr_period(col)
        curryr_rec = analysis_records.filtered(lambda l: l.period == period and l.product_id.id == product_id and l.trade_channel.id == 3)
        return round(curryr_rec.regular_sales,1)

    def _get_regular_curryear_actual_export(self,product_id, analysis_records,col):
        period = self._get_curryr_period(col)
        curryr_rec = analysis_records.filtered(lambda l: l.period == period and l.product_id.id == product_id and l.trade_channel.id == 4)
        return round(curryr_rec.regular_sales,1)

    def _get_regular_curryear_budg_total(self,product_id, analysis_records,col):
        result = self._get_regular_curryear_budg_export(product_id, analysis_records,col) + self._get_regular_curryear_budg_foodservice(product_id,analysis_records,col) \
                 + self._get_regular_curryear_budg_retail(product_id, analysis_records,col) + self._get_regular_curryear_budg_wholesale(product_id, analysis_records,col)
        return round(result,1)

    def _get_regular_curryear_budg_wholesale(self,product_id, analysis_records,col):
        period = self._get_curryr_period(col)
        curryr_rec = analysis_records.filtered(lambda l: l.period == period and l.product_id.id == product_id and l.trade_channel.id == 2)
        return round(curryr_rec.budget,1)

    def _get_regular_curryear_budg_retail(self,product_id, analysis_records,col):
        period = self._get_curryr_period(col)
        curryr_rec = analysis_records.filtered(lambda l: l.period == period and l.product_id.id == product_id and l.trade_channel.id == 1)
        return round(curryr_rec.budget,1)

    def _get_regular_curryear_budg_foodservice(self,product_id, analysis_records,col):
        period = self._get_curryr_period(col)
        curryr_rec = analysis_records.filtered(lambda l: l.period == period and l.product_id.id == product_id and l.trade_channel.id == 3)
        return round(curryr_rec.budget,1)

    def _get_regular_curryear_budg_export(self,product_id, analysis_records,col):
        period = self._get_curryr_period(col)
        curryr_rec = analysis_records.filtered(lambda l: l.period == period and l.product_id.id == product_id and l.trade_channel.id == 4)
        return round(curryr_rec.budget,1)

    def _get_regular_prevyear_variance_perc(self,product_id, analysis_records,col):
        get_regular_prevyear_budg_total = self._get_regular_prevyear_budg_total(product_id, analysis_records,col)
        if get_regular_prevyear_budg_total:
            result = round(self._get_regular_prevyear_variance_qty(product_id, analysis_records,col) / abs(get_regular_prevyear_budg_total) * 100)
        else:
            result= 0
        return result

    def _get_regular_prevyear_variance_qty(self,product_id, analysis_records,col):
        result = self._get_regular_prevyear_actual_total(product_id, analysis_records,col) - self._get_regular_prevyear_budg_total(product_id, analysis_records,col)
        return round(result,1)

    def _get_regular_prevyear_actual_total(self,product_id, analysis_records,col):
        result = self._get_regular_prevyear_actual_export(product_id, analysis_records,col) + self._get_regular_prevyear_actual_foodservice(product_id,analysis_records,col) \
                 + self._get_regular_prevyear_actual_retail(product_id, analysis_records,col) + self._get_regular_prevyear_actual_wholesale(product_id, analysis_records,col)
        return round(result,1)

    def _get_regular_prevyear_actual_wholesale(self,product_id, analysis_records,col):
        period = self._get_prevyr_period(col)
        lastyr_rec = analysis_records.filtered(lambda l: l.period == period and l.product_id.id == product_id and l.trade_channel.id == 2)
        return round(lastyr_rec.regular_sales,1)

    def _get_regular_prevyear_actual_retail(self,product_id, analysis_records,col):
        period = self._get_prevyr_period(col)
        lastyr_rec = analysis_records.filtered(lambda l: l.period == period and l.product_id.id == product_id and l.trade_channel.id == 1)
        return round(lastyr_rec.regular_sales,1)

    def _get_regular_prevyear_actual_foodservice(self,product_id, analysis_records,col):
        period = self._get_prevyr_period(col)
        lastyr_rec = analysis_records.filtered(lambda l: l.period == period  and l.product_id.id == product_id and l.trade_channel.id == 3)
        return round(lastyr_rec.regular_sales,1)

    def _get_regular_prevyear_actual_export(self,product_id, analysis_records,col):
        period = self._get_prevyr_period(col)
        lastyr_rec = analysis_records.filtered(lambda l: l.period == period and l.product_id.id == product_id and l.trade_channel.id == 4)
        return round(lastyr_rec.regular_sales,1)

    def _get_regular_prevyear_budg_total(self,product_id, analysis_records,col):
        result = self._get_regular_prevyear_budg_export(product_id, analysis_records,col) + self._get_regular_prevyear_budg_foodservice(product_id,analysis_records,col) \
                 + self._get_regular_prevyear_budg_retail(product_id, analysis_records,col) + self._get_regular_prevyear_budg_wholesale(product_id, analysis_records,col)
        return round(result,1)

    def _get_regular_prevyear_budg_wholesale(self,product_id, analysis_records,col):
        period = self._get_prevyr_period(col)
        lastyr_rec = analysis_records.filtered(lambda l: l.period == period and l.product_id.id == product_id and l.trade_channel.id == 2)
        return round(lastyr_rec.budget,1)

    def _get_regular_prevyear_budg_retail(self,product_id, analysis_records,col):
        period = self._get_prevyr_period(col)
        lastyr_rec = analysis_records.filtered(lambda l: l.period == period and l.product_id.id == product_id and l.trade_channel.id == 1)
        return round(lastyr_rec.budget,1)

    def _get_regular_prevyear_budg_foodservice(self,product_id, analysis_records,col):
        period = self._get_prevyr_period(col)
        lastyr_rec = analysis_records.filtered(lambda l: l.period == period and l.product_id.id == product_id and l.trade_channel.id == 3)
        return round(lastyr_rec.budget,1)

    def _get_regular_prevyear_budg_export(self,product_id, analysis_records,col):
        period = self._get_prevyr_period(col)
        lastyr_rec = analysis_records.filtered(lambda l: l.period == period and l.product_id.id == product_id and l.trade_channel.id == 4)
        return round(lastyr_rec.budget,1)

    def _get_promo_yroveryr_actual_perc(self, product_id, analysis_records,col):
        get_promo_prevyear_actual_total = self._get_promo_prevyear_actual_total(product_id, analysis_records,col)
        if get_promo_prevyear_actual_total:
            result = round(self._get_promo_yroveryr_actual_qty(product_id, analysis_records,col) / abs(get_promo_prevyear_actual_total) * 100)
        else:
            result= 0
        return result

    def _get_promo_yroveryr_actual_qty(self, product_id, analysis_records,col):
        result = self._get_promo_curryear_actual_total(product_id, analysis_records,col) - self._get_promo_prevyear_actual_total(product_id, analysis_records,col)
        return round(result,1)

    def _get_promo_yroveryr_budg_perc(self, product_id, analysis_records,col):
        get_promo_prevyear_budg_total = self._get_promo_prevyear_budg_total(product_id, analysis_records,col)
        if get_promo_prevyear_budg_total:
            result = round(self._get_promo_yroveryr_budg_qty(product_id, analysis_records,col) / abs(get_promo_prevyear_budg_total) * 100)
        else:
            result = 0
        return result

    def _get_promo_yroveryr_budg_qty(self, product_id, analysis_records,col):
        result = self._get_promo_curryear_budg_total(product_id, analysis_records,col) - self._get_promo_prevyear_budg_total(product_id,analysis_records,col)
        return round(result,1)

    def _get_promo_curryear_variance_perc(self, product_id, analysis_records,col):
        get_promo_curryear_budg_total = abs(self._get_promo_curryear_budg_total(product_id,analysis_records,col))
        if get_promo_curryear_budg_total:
            result = round((self._get_promo_curryear_variance_qty(product_id,analysis_records,col) / get_promo_curryear_budg_total) * 100)
        else:
            result = 0
        return result

    def _get_promo_curryear_variance_qty(self, product_id, analysis_records,col):
        result = self._get_promo_curryear_actual_total(product_id,analysis_records,col) - self._get_promo_curryear_budg_total(product_id,analysis_records,col)
        return round(result,1)

    def _get_promo_curryear_actual_total(self,product_id, analysis_records,col):
        result = self._get_promo_curryear_actual_priceoff(product_id,analysis_records,col) + self._get_promo_curryear_actual_pricecomp(product_id,analysis_records,col)
        return round(result,1)

    def _get_promo_curryear_actual_pricecomp(self,product_id,analysis_records,col):
        period = self._get_curryr_period(col)
        thisyr_rec = analysis_records.filtered(lambda l: l.period == period and l.product_id.id == product_id and l.trade_channel.id == 1)
        return round(thisyr_rec.price_comp,1)

    def _get_promo_curryear_actual_priceoff(self,product_id,analysis_records,col):
        period = self._get_curryr_period(col)
        thisyr_rec = analysis_records.filtered(lambda l: l.period == period and l.product_id.id == product_id and l.trade_channel.id == 1)
        return round(thisyr_rec.price_off,1)

    def _get_promo_curryear_budg_total(self,product_id,analysis_records,col):
        period = self._get_curryr_period(col)
        thisyr_rec = analysis_records.filtered(lambda l: l.period == period and l.product_id.id == product_id and l.trade_channel.id == 1)
        return round(thisyr_rec.budget,1)

    def _get_promo_prevyear_variance_perc(self, product_id, analysis_records,col):
        get_promo_prevyear_budg_total = abs(self._get_promo_prevyear_budg_total(product_id,analysis_records, col))
        if get_promo_prevyear_budg_total:
            result = round((self._get_promo_prevyear_variance_qty(product_id,analysis_records, col) / get_promo_prevyear_budg_total) * 100)
        else:
            result = 0
        return result

    def _get_promo_prevyear_variance_qty(self, product_id, analysis_records,col):
        result = self._get_promo_prevyear_actual_total(product_id,analysis_records,col) - self._get_promo_prevyear_budg_total(product_id,analysis_records,col)
        return round(result,1)

    def _get_promo_prevyear_actual_total(self,product_id, analysis_records,col):
        result = self._get_promo_prevyear_actual_priceoff(product_id,analysis_records,col) + self._get_promo_prevyear_actual_pricecomp(product_id,analysis_records,col)
        return round(result,1)

    def _get_promo_prevyear_actual_pricecomp(self,product_id,analysis_records,col):
        period = self._get_prevyr_period(col)
        lastyr_rec = analysis_records.filtered(lambda l: l.period == period and l.product_id.id == product_id and l.trade_channel.id == 1)
        return round(lastyr_rec.price_comp,1)

    def _get_promo_prevyear_actual_priceoff(self,product_id,analysis_records,col):
        period = self._get_prevyr_period(col)
        lastyr_rec = analysis_records.filtered(lambda l: l.period == period and l.product_id.id == product_id and l.trade_channel.id == 1)
        return round(lastyr_rec.price_off,1)

    def _get_promo_prevyear_budg_total(self,product_id,analysis_records,col):
        period = self._get_prevyr_period(col)
        lastyr_rec = analysis_records.filtered(lambda l: l.period == period and l.product_id.id == product_id and l.trade_channel.id == 1)
        return round(lastyr_rec.budget,1)

    def _get_nearexp_yroveryr_perc(self, product_id,analysis_records,col):
        get_nearerp_prevyear = abs(self._get_nearexp_prevyear(product_id, analysis_records,col))
        if get_nearerp_prevyear:
            result = round((self._get_nearexp_yroveryr_qty(product_id, analysis_records,col) / get_nearerp_prevyear) * 100,1)
        else:
            result = 0
        return round(result,0)

    def _get_nearexp_yroveryr_qty(self,product_id, analysis_records, col):
        result = self._get_nearexp_curryear(product_id, analysis_records,col) - self._get_nearexp_prevyear(product_id, analysis_records,col)
        return round(result,1)

    def _get_nearexp_curryear(self, product_id, analysis_records, col):
        period = self._get_curryr_period(col)
        #thisyr_rec = analysis_records.filtered(lambda l: l.period == period and l.product_id.id == product_id and l.trade_channel.id == 1)
        # Near expiry should consider all trade channels
        thisyr_rec = analysis_records.filtered(lambda l: l.period == period and l.product_id.id == product_id)
        near_exp_value = 0
        for rec in thisyr_rec:
            near_exp_value += rec.near_expiry
        return round(near_exp_value, 1)

    def _get_nearexp_prevyear(self, product_id, analysis_records, col):
        period = self._get_prevyr_period(col)
        #lastyr_rec = analysis_records.filtered(lambda l: l.period == period and l.product_id.id == product_id and l.trade_channel.id == 1)
        # Near expiry should consider all trade channels
        lastyr_rec = analysis_records.filtered(
            lambda l: l.period == period and l.product_id.id == product_id)
        near_exp_value = 0
        for rec in lastyr_rec:
            near_exp_value += rec.near_expiry
        return round(near_exp_value, 1)

    def initialize_cols_lists(self,cols):
        cols["nearexp_prevyear"]=[]
        cols["nearexp_curryear"]=[]
        cols["nearexp_yroveryr_qty"]=[]
        cols["nearexp_yroveryr_perc"]=[]
        cols["promo_prevyear_budg_total"]=[]
        cols["promo_prevyear_actual_priceoff"]=[]
        cols["promo_prevyear_actual_pricecomp"]=[]
        cols["promo_prevyear_actual_total"]=[]
        cols["promo_prevyear_variance_qty"]=[]
        cols["promo_prevyear_variance_perc"]=[]
        cols["promo_curryear_budg_total"]=[]
        cols["promo_curryear_actual_priceoff"]=[]
        cols["promo_curryear_actual_pricecomp"]=[]
        cols["promo_curryear_actual_total"]=[]
        cols["promo_curryear_variance_qty"]=[]
        cols["promo_curryear_variance_perc"]=[]
        cols["promo_yroveryr_budg_qty"]=[]
        cols["promo_yroveryr_budg_perc"]=[]
        cols["promo_yroveryr_actual_qty"]=[]
        cols["promo_yroveryr_actual_perc"]=[]
        cols["regular_prevyear_budg_export"]=[]
        cols["regular_prevyear_budg_foodservice"]=[]
        cols["regular_prevyear_budg_retail"]=[]
        cols["regular_prevyear_budg_wholesale"]=[]
        cols["regular_prevyear_budg_total"]=[]
        cols["regular_prevyear_actual_export"]=[]
        cols["regular_prevyear_actual_foodservice"]=[]
        cols["regular_prevyear_actual_retail"]=[]
        cols["regular_prevyear_actual_wholesale"]=[]
        cols["regular_prevyear_actual_total"]=[]
        cols["regular_prevyear_variance_qty"]=[]
        cols["regular_prevyear_variance_perc"]=[]
        cols["regular_curryear_budg_export"]=[]
        cols["regular_curryear_budg_foodservice"]=[]
        cols["regular_curryear_budg_retail"]=[]
        cols["regular_curryear_budg_wholesale"]=[]
        cols["regular_curryear_budg_total"]=[]
        cols["regular_curryear_actual_export"]=[]
        cols["regular_curryear_actual_foodservice"]=[]
        cols["regular_curryear_actual_retail"]=[]
        cols["regular_curryear_actual_wholesale"]=[]
        cols["regular_curryear_actual_total"]=[]
        cols["regular_curryear_variance_qty"]=[]
        cols["regular_curryear_variance_perc"]=[]
        cols["regular_yroveryr_budget_qty"]=[]
        cols["regular_yroveryr_budget_perc"]=[]
        cols["regular_yroveryr_actual_qty"]=[]
        cols["regular_yroveryr_actual_perc"]=[]
        cols["total_prevyear_budg_total"]=[]
        cols["total_prevyear_actual_total"]=[]
        cols["total_prevyear_variance_quantity"]=[]
        cols["total_prevyear_variance_perc"]=[]
        cols["total_curryear_budg_total"]=[]
        cols["total_curryear_actual_total"]=[]
        cols["total_curryear_variance_quantity"]=[]
        cols["total_curryear_variance_perc"]=[]
        cols["total_yroveryr_budg_quantity"]=[]
        cols["total_yroveryr_budg_perc"]=[]
        cols["total_yroveryr_actual_quantity"]=[]
        cols["total_yroveryr_actual_perc"]=[]

    def _get_curryr_period(self, num):
        num -= 1
        today = datetime.today()
        first_day_of_current_month = today.replace(day=1)
        target_date = first_day_of_current_month - relativedelta(months=num)
        first_day_of_previous_month = target_date.replace(day=1)
        return first_day_of_previous_month.strftime('%Y-%m')

    def _get_prevyr_period(self,num):
        num -= 1
        today = datetime.today()
        first_day_of_current_month = today.replace(day=1)
        first_day_of_previous_year = first_day_of_current_month - relativedelta(years=1)
        target_date = first_day_of_previous_year - relativedelta(months=num)
        first_day_of_previous_month = target_date.replace(day=1)
        return first_day_of_previous_month.strftime('%Y-%m')

    def _get_month_full_name(self,col):
        months_ago = datetime.now() - relativedelta(months=col)
        month_name = months_ago.strftime('%B').upper()
        return month_name
    def _get_month_short_name(self,col):
        months_ago = datetime.now() - relativedelta(months=col)
        month_abbreviation = months_ago.strftime('%b').upper()
        return month_abbreviation

    def _get_purchase_records(self):
        product_ids = tuple(self.product_ids.ids)  # Convert list to a tuple
        query = """
                SELECT pol.product_id, SUM((pi_qty - (pol.qty_received / pp.qty)))::numeric(10,2) AS to_rcv
                FROM purchase_order_line AS pol 
                JOIN purchase_order AS po ON pol.order_id = po.id
                JOIN product_packaging AS pp ON pol.product_packaging_id = pp.id
                WHERE po.state = 'purchase' AND po.receiving_status in ('partial','not_received')
                AND (pol.qty_received / pp.qty != pi_qty) AND pol.product_id in %s
                GROUP BY pol.product_id
            """
        self.env.cr.execute(query, (product_ids,))
        result = self.env.cr.dictfetchall()
        return result

    def _get_stock_totals_product(self):
        product_ids = tuple(self.product_ids.ids)
        # query = """
        #             SELECT q.product_id, COALESCE(sum(q.quantity),0) / ppl.pcp as onhand
        #             FROM sry_forecast_location_stock_location_rel AS r
        #             JOIN sry_forecast_location AS f ON r.sry_forecast_location_id = f.id
        #             LEFT JOIN stock_quant AS q ON q.location_id = r.stock_location_id
        #             LEFT JOIN (SELECT MAX(pp.qty) as pcp, pp.product_id as product_id
        #                     FROM product_packaging as pp
        #                     WHERE pp.product_id is not NULL
        #                     GROUP BY pp.product_id) AS ppl ON q.product_id = ppl.product_id
        #             WHERE f.total = true AND f.report = 'forecast' AND q.product_id in %s
        #             GROUP BY q.product_id, ppl.pcp
        #             ORDER BY q.product_id
        #         """
        # 08/03/24 - Pranav: Above SQL changed as below after stock location has been changed.
        query = """
                SELECT s.product_id, COALESCE(sum(s.puom_qty),0) / ppl.pcp as onhand  
                FROM sry_forecast_location_stock_location_rel AS r 
                JOIN sry_forecast_location AS f ON r.sry_forecast_location_id = f.id
                LEFT JOIN (
                    SELECT sq.product_id, sl.location_id, COALESCE(SUM(sq.quantity),0) AS puom_qty
                    FROM stock_location sl 
                    LEFT JOIN stock_quant sq ON sq.location_id = sl.id
                    WHERE sl.location_id not in (1,2,3,7)
                    GROUP BY sq.product_id, sl.location_id
                    ORDER BY sq.product_id, sl.location_id) AS s ON r.stock_location_id = s.location_id
                LEFT JOIN (SELECT MAX(pp.qty) as pcp, pp.product_id as product_id
                    FROM product_packaging as pp
                    WHERE pp.product_id is not NULL
                    GROUP BY pp.product_id) AS ppl ON s.product_id = ppl.product_id
                WHERE f.total = true AND f.report = 'forecast' AND s.product_id in %s
                GROUP BY s.product_id,ppl.pcp
                ORDER BY s.product_id
        """
        self.env.cr.execute(query, (product_ids,))
        result = self.env.cr.dictfetchall()
        return result

    def _get_location_wise_stocks(self):
        product_ids = tuple(self.product_ids.ids)
        # query = """
        #     SELECT q.product_id,f.name, COALESCE(sum(q.quantity),0) / ppl.pcp as onhand
        #     FROM sry_forecast_location_stock_location_rel AS r
        #     JOIN sry_forecast_location AS f ON r.sry_forecast_location_id = f.id
        #     LEFT JOIN stock_quant AS q ON q.location_id = r.stock_location_id
        #     LEFT JOIN (SELECT MAX(pp.qty) as pcp, pp.product_id as product_id
        #             FROM product_packaging as pp
        #             WHERE pp.product_id is not NULL
        #             GROUP BY pp.product_id) AS ppl ON q.product_id = ppl.product_id
        #     WHERE (f.total = false OR f.total is null) AND f.report = 'forecast' AND q.product_id in %s
        #     GROUP BY q.product_id,f.name,ppl.pcp
        #     ORDER BY q.product_id,f.name
        # """
        # 19/01/24 - Rigeesh: Above SQL changed as below after stock location has been changed.
        query = """
                SELECT s.product_id,f.name, COALESCE(sum(s.puom_qty),0) / ppl.pcp as onhand  
                FROM sry_forecast_location_stock_location_rel AS r 
                JOIN sry_forecast_location AS f ON r.sry_forecast_location_id = f.id
                LEFT JOIN (
                    SELECT sq.product_id, sl.location_id, COALESCE(SUM(sq.quantity),0) AS puom_qty
                    FROM stock_location sl 
                    LEFT JOIN stock_quant sq ON sq.location_id = sl.id
                    WHERE sl.location_id not in (1,2,3,7)
                    GROUP BY sq.product_id, sl.location_id
                    ORDER BY sq.product_id, sl.location_id) AS s ON r.stock_location_id = s.location_id
                LEFT JOIN (SELECT MAX(pp.qty) as pcp, pp.product_id as product_id
                    FROM product_packaging as pp
                    WHERE pp.product_id is not NULL
                    GROUP BY pp.product_id) AS ppl ON s.product_id = ppl.product_id
                WHERE (f.total = false OR f.total is null) AND f.report = 'forecast' AND s.product_id in %s
                GROUP BY s.product_id,f.name,ppl.pcp
                ORDER BY s.product_id,f.name
        """
        self.env.cr.execute(query,(product_ids,))
        result = self.env.cr.dictfetchall()
        return result

    def _get_picking_records(self):
        product_ids = tuple(self.product_ids.ids)  # Convert list to a tuple
        query =  """
            SELECT MIN(TO_CHAR(sp.scheduled_date,'YYYY-MM-DD')) AS scheduled_date, sm.product_id AS product_id
            FROM stock_picking AS sp 
            INNER JOIN stock_move AS sm ON sm.picking_id=sp.id 
            INNER JOIN stock_picking_type AS spt ON sp.picking_type_id = spt.id
            WHERE sp.state = 'done' AND spt.code = 'outgoing' AND sm.product_id in %s
            GROUP BY sm.product_id 
            ORDER BY sm.product_id
        """
        self.env.cr.execute(query,(product_ids,))
        result = self.env.cr.dictfetchall()
        return result

    def _get_next_3months_budget_avgs_records(self):
        product_ids = tuple(self.product_ids.ids)  # Convert list to a tuple
        query =  """
            SELECT product_id, SUM(quantity) / 3 AS avg
            FROM sry_sales_budget_line
            WHERE ((budget_year = EXTRACT(YEAR FROM (CURRENT_DATE + INTERVAL '1 month'))::text AND budget_month = TO_CHAR(EXTRACT(MONTH FROM (CURRENT_DATE + INTERVAL '1 month')), 'FM00')) OR
                  (budget_year = EXTRACT(YEAR FROM (CURRENT_DATE + INTERVAL '2 month'))::text AND budget_month = TO_CHAR(EXTRACT(MONTH FROM (CURRENT_DATE + INTERVAL '2 month')),'FM00')) OR
                  (budget_year = EXTRACT(YEAR FROM (CURRENT_DATE + INTERVAL '3 month'))::text AND budget_month = TO_CHAR(EXTRACT(MONTH FROM (CURRENT_DATE + INTERVAL '3 month')),'FM00')))
                  AND product_id in %s
            GROUP BY product_id
        """
        self.env.cr.execute(query,(product_ids,))
        result = self.env.cr.dictfetchall()
        return result

    def _get_next_average_budget(self, product_id, next_3months_budget_avgs_records):
        matching_record = next((record for record in next_3months_budget_avgs_records if record['product_id'] == product_id), None)
        result = matching_record and matching_record['avg'] or 0
        return result