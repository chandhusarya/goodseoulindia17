# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class PosOrderReport(models.Model):
    _name = "pos.order.report"
    _description = "Point of Sale Order Report"
    _auto = False
    _order = 'date desc'
    _rec_name = 'order_id'

    date = fields.Datetime(
        string='Order Date',
        readonly=True
    )
    order_id = fields.Many2one(
        comodel_name='pos.order',
        string='Order',
        readonly=True
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer',
        readonly=True
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        readonly=True
    )
    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string='Product Template',
        readonly=True
    )
    state = fields.Selection(
        selection=[
            ('draft', 'New'),
            ('paid', 'Paid'),
            ('done', 'Posted'),
            ('invoiced', 'Invoiced'),
            ('cancel', 'Cancelled')
        ],
        string='Status',
        readonly=True
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='User',
        readonly=True
    )
    price_total = fields.Float(
        string='Total Price',
        readonly=True
    )
    price_sub_total = fields.Float(
        string='Subtotal w/o discount',
        readonly=True
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        readonly=True
    )
    nbr_lines = fields.Integer(
        string='Sale Line Count',
        readonly=True
    )
    product_qty = fields.Integer(
        string='Product Quantity',
        readonly=True
    )
    product_categ_id = fields.Many2one(
        comodel_name='product.category',
        string='Product Category',
        readonly=True
    )
    config_id = fields.Many2one(
        comodel_name='pos.config',
        string='Point of Sale',
        readonly=True
    )
    session_id = fields.Many2one(
        comodel_name='pos.session',
        string='Session',
        readonly=True
    )
    combo_parent_line_id = fields.Many2one(
        comodel_name='pos.order.line',
        string='Combo Parent',
        readonly=True
    )
    combo_product_id = fields.Many2one(
        comodel_name='product.product',
        string='Combo Product',
        readonly=True
    )

    def _select(self):
        return """  SELECT
                        MIN(pol.id) AS id,
                        COUNT(*) AS nbr_lines,
                        po.date_order AS date,
                        SUM(pol.qty) AS product_qty,
                        CASE
                            WHEN EXISTS (SELECT 1 FROM pos_order_line children WHERE children.combo_parent_id = pol.id)
                                THEN (SELECT SUM(children.qty * children.price_unit)
                                      FROM pos_order_line children
                                      WHERE children.combo_parent_id = pol.id)
                            WHEN pol.combo_parent_id IS NOT NULL THEN 0.00  -- Child line gets 0
                            ELSE (pol.qty * pol.price_unit) / CASE COALESCE(po.currency_rate, 0) WHEN 0 THEN 1.0 ELSE po.currency_rate END
                        END AS price_sub_total,
                        CASE
                            WHEN EXISTS (SELECT 1 FROM pos_order_line children WHERE children.combo_parent_id = pol.id)
                                THEN (SELECT SUM(children.qty * children.price_unit)
                                      FROM pos_order_line children
                                      WHERE children.combo_parent_id = pol.id)
                            WHEN pol.combo_parent_id IS NOT NULL THEN 0.00  -- Child line gets 0
                            ELSE pol.qty * pol.price_unit
                        END AS price_total,
                        po.id AS order_id,
                        po.partner_id AS partner_id,
                        po.state AS state,
                        po.user_id AS user_id,
                        po.company_id AS company_id,
                        pol.product_id AS product_id,
                        ppt.categ_id AS product_categ_id,
                        pp.product_tmpl_id AS product_tmpl_id,
                        ps.config_id AS config_id,
                        po.session_id AS session_id,
                        pol.combo_parent_id AS combo_parent_line_id,
                        pol2.product_id as combo_product_id """

    def _from(self):
        return """  FROM
                        pos_order_line pol
                    LEFT JOIN
                        pos_order po ON pol.order_id = po.id
                    LEFT JOIN
                        product_product pp ON pol.product_id = pp.id
                    LEFT JOIN
                        product_template ppt ON pp.product_tmpl_id = ppt.id
                    LEFT JOIN 
                        pos_session ps ON (po.session_id=ps.id)
                    LEFT JOIN
                        res_company co ON (po.company_id=co.id)
                    LEFT JOIN 
                        res_currency cu ON (co.currency_id=cu.id) 
                    LEFT JOIN 
                    	pos_order_line pol2 on pol2.id = pol.combo_parent_id """


    def _group_by(self):
        return """  GROUP BY
                        po.id,
                        po.date_order,
                        po.partner_id,
                        po.state,
                        pol.id,
                        ppt.categ_id,
                        po.user_id,
                        po.company_id,
                        po.create_date,
                        po.session_id,
                        pol.product_id,
                        pp.product_tmpl_id,
                        ps.config_id,
                        pol.combo_parent_id,
                        pol2.product_id """

    def _order_by(self):
        return """  ORDER BY
                        pol.id desc """

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        query =  """
            CREATE OR REPLACE VIEW %s AS (
                %s
                %s
                %s
                %s
            )
        """ % (self._table, self._select(), self._from(), self._group_by(), self._order_by())
        self._cr.execute(query)
