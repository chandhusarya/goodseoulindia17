from odoo import models, fields, api, tools
from datetime import datetime

class sryForecastAnalysis(models.Model):
    _name = "sry.forecast.analysis"
    _description = "Sarya Forecast Analysis"
    _auto = False
    _order = 'period,product_id,trade_channel'


    period = fields.Char(string="Period")
    quantity = fields.Integer(string="Quantity")
    ctn_uom = fields.Integer(string="Carton UOM")
    ctn_qty = fields.Integer(string="Carton Qty")
    product_id = fields.Many2one('product.product', string="Product")
    trade_channel = fields.Many2one('trade.channel',string="Trade Channel")
    near_expiry = fields.Integer(string="Near Expiry")
    regular_sales = fields.Integer(string="Regular Sales")
    price_comp = fields.Integer(string="Price Comp")
    price_off = fields.Integer(string="Price Off")
    budget = fields.Integer(string="Budget")
    # lastyr_3mo_ago_near_expiry_sale = fields.Integer(string='-1y-3mo NES', compute='_compute_lastyr_3mo_ago_near_expiry_sale')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = """
            CREATE OR REPLACE VIEW sry_forecast_analysis AS (
                
                WITH cost_values AS (
                        SELECT 
                        aml_cost.move_id,
                        aml_cost.product_id,
                        cost_value,
                        quantity,
                        cost_value / NULLIF(quantity, 0) AS unit_cost
                        FROM (
                            SELECT 
                                aml.move_id,
                                aml.product_id,
                                SUM(CASE WHEN aml.move_type = 'out_invoice' THEN aml.debit ELSE -aml.credit END) AS cost_value
                            FROM 
                                account_move_line AS aml
                            WHERE 
                                aml.account_id IN (SELECT id FROM account_account WHERE user_type_id = 17)
                            GROUP BY 
                                aml.move_id, aml.product_id
                        ) AS aml_cost
                        JOIN (
                            SELECT 
                                move_id, 
                                product_id, 
                                SUM(quantity) AS quantity
                            FROM 
                                account_move_line
                            WHERE 
                                account_id IN (SELECT id FROM account_account WHERE user_type_id = 13)
                            GROUP BY 
                                move_id, product_id
                        ) AS aml_quantity
                        ON aml_cost.move_id = aml_quantity.move_id AND aml_cost.product_id = aml_quantity.product_id
                    )
                    
                    SELECT 
                        row_number() OVER (ORDER BY a.product_id) AS id,
                        TO_CHAR(a.date,'YYYY-MM') AS period,
                        SUM((CASE WHEN a.move_type = 'out_invoice' THEN a.quantity ELSE -a.quantity END) / ppl.pcp) as ctn_qty,
                        ppl.pcp AS ctn_uom,
                        SUM(CASE WHEN a.move_type = 'out_invoice' THEN a.quantity ELSE -a.quantity END) as quantity,
                        a.product_id as product_id,
                        rp.trade_channel as trade_channel,
                        SUM(
                            CASE
                                WHEN (CASE WHEN a.move_type = 'out_invoice' THEN a.credit ELSE -a.debit END) = 0.00
                                THEN (CASE WHEN a.move_type = 'out_invoice' THEN a.quantity ELSE -a.quantity END) / ppl.pcp
                                ELSE 0
                            END) +
                        SUM(
                            CASE
                                WHEN (CASE WHEN a.move_type = 'out_invoice' THEN a.credit ELSE -a.debit END) <> 0
                                    AND (
                                        (CASE WHEN a.move_type = 'out_invoice' THEN a.credit ELSE -a.debit END - COALESCE(cv.unit_cost * a.quantity, 0)) /
                                        (CASE WHEN a.move_type = 'out_invoice' THEN a.credit ELSE -a.debit END)
                                    ) < 0.1
                                THEN (CASE WHEN a.move_type = 'out_invoice' THEN a.quantity ELSE -a.quantity END) / ppl.pcp
                                ELSE 0
                            END) as near_expiry,
                        SUM(
                            CASE
                                WHEN (CASE WHEN a.move_type = 'out_invoice' THEN a.credit ELSE -a.debit END) <> 0
                                    AND (
                                        (CASE WHEN a.move_type = 'out_invoice' THEN a.credit ELSE -a.debit END - COALESCE(cv.unit_cost * a.quantity, 0)) /
                                        (CASE WHEN a.move_type = 'out_invoice' THEN a.credit ELSE -a.debit END)
                                    ) >= 0.1
                                THEN (CASE WHEN a.move_type = 'out_invoice' THEN a.quantity ELSE -a.quantity END) / ppl.pcp 
                                ELSE 0
                            END) - SUM(
                            CASE
                                WHEN a.promo = 'off'
                                THEN (CASE WHEN a.move_type = 'out_invoice' THEN a.quantity ELSE -a.quantity END) / ppl.pcp
                                ELSE 0
                            END) - SUM(
                            CASE
                                WHEN a.promo = 'comp'
                                THEN (CASE WHEN a.move_type = 'out_invoice' THEN a.quantity ELSE -a.quantity END) / ppl.pcp
                                ELSE 0
                            END) as regular_sales,
                        SUM(
                            CASE
                                WHEN a.promo = 'comp'
                                THEN (CASE WHEN a.move_type = 'out_invoice' THEN a.quantity ELSE -a.quantity END) / ppl.pcp
                                ELSE 0
                            END) as price_comp,
                        SUM(
                            CASE
                                WHEN a.promo = 'off'
                                THEN (CASE WHEN a.move_type = 'out_invoice' THEN a.quantity ELSE -a.quantity END) / ppl.pcp
                                ELSE 0
                            END) as price_off,
                        COALESCE(bd.budget,0) AS budget
                    FROM 
                        account_move_line AS a
                    INNER JOIN 
                        res_partner AS rp ON a.partner_id = rp.id
                    LEFT JOIN 
                        cost_values AS cv ON a.move_id = cv.move_id AND a.product_id = cv.product_id
                    
                        
                        
                    LEFT JOIN (
                        SELECT MAX(pp.qty) as pcp, pp.product_id as product_id
                        FROM product_packaging as pp
                        WHERE pp.product_id is not NULL
                        GROUP BY pp.product_id
                    ) AS ppl ON a.product_id = ppl.product_id
                    LEFT JOIN (
                        SELECT CONCAT(budget_year,'-',budget_month) as period, trade_channel_id, product_id, sum(quantity) AS budget
                        FROM sry_sales_budget_line
                        GROUP BY trade_channel_id, product_id,budget_year,budget_month
                    ) AS bd ON TO_CHAR(a.date,'YYYY-MM') = bd.period AND  rp.trade_channel = bd.trade_channel_id AND a.product_id = bd.product_id
                    WHERE 
                        a.move_type IN ('out_refund', 'out_invoice') AND a.parent_state = 'posted' 
                        AND a.account_id IN (SELECT id FROM account_account WHERE user_type_id = 13)
                    GROUP BY 
                        a.product_id, rp.trade_channel, TO_CHAR(a.date,'YYYY-MM'), bd.budget, ppl.pcp
                    ORDER BY 
                        TO_CHAR(a.date,'YYYY-MM')
                
                
        );"""
        self.env.cr.execute(query)

