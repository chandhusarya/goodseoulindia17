from odoo import fields, models, api
import io
import json
import xlsxwriter


class POSDailySalesReport(models.TransientModel):
    _name = 'pos.daily.sales.report'
    _description = 'Daily Sales Report'

    def _default_start_date(self):
        """ Find the earliest start_date of the latests sessions """
        # restrict to configs available to the user
        config_ids = self.env['pos.config'].search([]).ids
        # exclude configs has not been opened for 2 days
        self.env.cr.execute("""
            SELECT
            max(start_at) as start,
            config_id
            FROM pos_session
            WHERE config_id = ANY(%s)
            AND start_at > (NOW() - INTERVAL '2 DAYS')
            GROUP BY config_id
        """, (config_ids,))
        latest_start_dates = [res['start'] for res in self.env.cr.dictfetchall()]
        # earliest of the latest sessions
        return latest_start_dates and min(latest_start_dates) or fields.Datetime.now()

    from_date = fields.Date(
        string='From Date',
        required=True, default=_default_start_date)
    to_date = fields.Date(
        string='To Date',
        required=True, default=fields.Datetime.now)
    outlet_ids = fields.Many2many(
        comodel_name='pos.config',
        string='Outlet', default=lambda s: s.env['pos.config'].search([]))

    @api.onchange('from_date')
    def _onchange_from_date(self):
        if self.from_date and self.to_date and self.to_date < self.from_date:
            self.to_date = self.from_date

    @api.onchange('end_date')
    def _onchange_end_date(self):
        if self.to_date and self.from_date and self.to_date < self.from_date:
            self.from_date = self.to_date

    def generate_report(self):
        data = {'date_start': self.from_date.strftime('%Y-%m-%d 00:00:00'), 'date_stop': self.to_date.strftime('%Y-%m-%d 23:59:59'), 'config_ids': self.outlet_ids.ids}
        return self.env.ref('sarya_pos_report.daily_sales_report').report_action([], data=data)
    def generate_report_new(self):
        from_date = self.from_date
        to_date = self.to_date
        outlet_ids = self.outlet_ids
        data = []
        for outlet in outlet_ids:
            order_lines = self.env['pos.order.line']
            orders = self.env['pos.order']
            outlet_data = {}
            sessions = self.env['pos.session'].search([('config_id', '=', outlet.id),
                                                       ('start_at', '>=', from_date), ('stop_at', '<=', to_date)])
            if len(sessions.ids) > 0:
                order_lines = order_lines.search([('order_id.session_id', 'in', sessions.ids)])
                if len(order_lines) > 0:
                    orders = orders.browse(list(set(line.order_id.id for line in order_lines)))
                    outlet_data[outlet.name] = {}
                    outlet_data[outlet.name]['total_revenue'] = round(sum(orders.mapped('amount_total')), 2)
                    outlet_data[outlet.name]['tax_collected'] = round(sum(orders.mapped('amount_tax')), 2)
                    outlet_data[outlet.name]['net_sales'] = round(sum(orders.mapped('amount_total')) - sum(orders.mapped('amount_tax')), 2)
                    outlet_data[outlet.name]['transactions'] = len(orders)
                    outlet_data[outlet.name]['products'] = order_lines._read_group(domain=[('order_id.session_id', 'in', sessions.ids)],
                                                  groupby=['product_id'])
                    data.append(outlet_data)




