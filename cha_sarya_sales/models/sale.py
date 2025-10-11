import pytz
from odoo import api, fields, models, _, SUPERUSER_ID
from datetime import date, datetime, timedelta
from odoo.exceptions import UserError
from twilio.rest import Client
import json


class ResPartner(models.Model):
    _inherit = 'res.partner'

    delivery_lead_time = fields.Integer("Delivery Lead Time(Hrs)", tracking=True)
    stock_count_date = fields.Date('Stock Count Date')

class SaleOrderInherit(models.Model):
    _inherit = "sale.order"

    delivery_lead_time = fields.Integer(string="Delivery Lead Time(Hrs)", related='partner_id.delivery_lead_time', tracking=True)
    customer_lpo_date = fields.Date(string='LPO Date', tracking=True)
    delivery_deadline_date = fields.Datetime(string='Delivery Deadline', tracking=True)

    delivery_plan_new = fields.Many2one('sry.coverage.plan',
                                    string="Merch Delivery Plan",
                                    domain="[('outlet_id', '=', partner_id), ('type', '=', 'delivery'),"
                                           "('date', '>', date_order)]")
    total_product_weight = fields.Float(string="Total Weight", compute="_compute_total_product_weight")
    total_product_gross_weight = fields.Float(string="Total Weight", compute="_compute_total_product_weight")


    def send_notification(self, employee, message, subject, button_url):
            # Email notification
            mail_content = "Dear " + str(employee.name)
            print("message =========>> ", message)
            mail_content += "<br/><br/>" + message
            main_content = {
                "subject": subject,
                "body_html": mail_content,
                "email_to": employee.work_email,
            }
            self.env['mail.mail'].sudo().create(main_content).send()

            #Whatsapp message
            account_sid = self.env['ir.config_parameter'].sudo().get_param('twilio.account_sid', False)
            auth_token = self.env['ir.config_parameter'].sudo().get_param('twilio.auth_token', False)
            from_number = self.env['ir.config_parameter'].sudo().get_param('twilio.from', False)
            if employee.whatsapp_number:
                to_number = employee.whatsapp_number
            else:
                # Fallback to mobile or work phone if whatsapp number is not available
                to_number = employee.mobile_phone and employee.mobile_phone or employee.work_phone

            if account_sid and auth_token and from_number and to_number:
                from_number = "whatsapp:%s" % from_number
                to_number = to_number.replace(" ", '')
                to_number = "whatsapp:%s" % to_number
                content_variables = json.dumps({"1": message,
                                     "2": button_url})
                client = Client(account_sid, auth_token)
                tillow_message = client.messages.create(
                    from_=from_number,
                    content_sid='HXbecfa3982f02c410ede41a204763e958',
                    content_variables=content_variables,
                    to=to_number)


    def action_confirm(self):
        """passing picking id to delivery order"""
        res = super(SaleOrderInherit, self).action_confirm()
        for order in self:
            picking_ids = order.picking_ids
            if picking_ids:
                users = self.env.ref('cha_sarya_sales.get_sales_order_confirmation_notification').users
                employee_ids = []
                for user in users:
                    if order.company_id.id in user.company_ids.ids:
                        employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
                        if employee:
                            employee_ids.append(employee.id)
                        else:
                            raise UserError(_("User %s does not have an employee record.") % user.name)
                if employee_ids:
                    employees = self.env['hr.employee'].browse(employee_ids)
                    for employee in employees:
                        message = "Hi %s, Sales order %s is confirmed. Please process delivery Order %s" % (employee.name, order.name, picking_ids[0].name)
                        subject = "Sales Order Confirmation Notification for %s" % order.name
                        button_url = "#id=%s&cids=1&menu_id=280&action=416&model=stock.picking&view_type=form" % (str(picking_ids[0].id))
                        self.send_notification(employees, message, subject, button_url)
        return res


    def _compute_total_product_weight(self):
        for move in self:
            weight, gross_weight = 0, 0
            for line in move.order_line:
                if line.product_id and line.product_packaging_id:
                    pack_qty = line.product_packaging_id.qty
                    weight += (line.product_id.weight)*pack_qty*line.product_packaging_qty
                    gross_weight += (line.product_id.gross_weight)*pack_qty*line.product_packaging_qty
            move.total_product_weight = weight
            move.total_product_gross_weight = gross_weight

    @api.onchange('delivery_plan_new')
    def onchange_delivery_plan(self):
        for so in self:
            if so.delivery_plan_new:
                so.commitment_date = so.delivery_plan_new.date
                if so.partner_id and so.partner_id.stock_count_date:
                    commit_date = self.commitment_date.date()
                    if so.partner_id.stock_count_date == commit_date:
                        res = {}
                        res['warning'] = {'title': _('Warning'),
                                          'message': _('Delivery date and Stock Count day of the customer is same.')}
                    return res



    @api.onchange('customer_lpo_date')
    def onchange_customer_lpo_date(self):
        for so in self:

            #Check is there any delivery plan
            delivery_plan = self.env['sry.coverage.plan'].search([('outlet_id', '=', so.partner_id.id),
                                                                  ('type', '=', 'delivery'),
                                                                  ('date', '>', so.date_order)],
                                                                  order = 'date asc', limit=1)
            if delivery_plan:
                so.delivery_plan_new = delivery_plan.id
            else:
                if so.delivery_lead_time > 1 and so.customer_lpo_date:
                    delivery_lead_time = so.delivery_lead_time
                    customer_lpo_date = so.customer_lpo_date
                    customer_lpo_date = datetime.combine(customer_lpo_date, datetime.min.time())
                    commitment_date = customer_lpo_date + timedelta(hours=delivery_lead_time)
                    so.commitment_date = commitment_date
                else:
                    so.commitment_date = False
            if so.partner_id and so.partner_id.stock_count_date:
                commit_date = self.commitment_date.date()
                if so.partner_id.stock_count_date == commit_date:
                    res = {}
                    res['warning'] = {'title': _('Warning'), 'message': _('Delivery date and Stock Count day of the customer is same.')}
                    return res


    @api.onchange('commitment_date')
    def onchange_commitment_date_so(self):
        for so in self:
            if so.commitment_date:
                delivery_deadline_date = so.commitment_date + timedelta(hours=24)
                so.delivery_deadline_date = delivery_deadline_date
                if so.partner_id.stock_count_date ==  delivery_deadline_date.date():
                    res = {}
                    res['warning'] = {'title': _('Warning'), 'message': _(
                        'Delivery deadline date and Stock Count day of the customer is same.')}
                    return res
            else:
                so.delivery_deadline_date = False

    def write(self, values):
        res = super(SaleOrderInherit, self).write(values)
        for so in self:
            if so.delivery_deadline_date and  so.order_line.move_ids:
                so.order_line.move_ids.date_deadline = so.delivery_deadline_date
        return res

    @api.model
    def _prepare_purchase_order_line_data(self, so_line, date_order, company):
        res = super(SaleOrderInherit, self)._prepare_purchase_order_line_data(so_line, date_order, company)
        res['product_packaging_id'] = so_line.product_packaging_id and so_line.product_packaging_id.id
        return res



class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def write(self, values):
        res = super(SaleOrderLine, self).write(values)
        for so_line in self:
            if so_line.move_ids:
                so_line.move_ids.date_deadline = so_line.order_id.delivery_deadline_date
        return res

    @api.depends('product_id', 'product_uom_qty', 'product_uom')
    def _compute_product_packaging_id(self):
        for line in self:
            #Inherited function in order avoid auto carton caluclation
            if line.product_packaging_id.product_id != line.product_id:
                line.product_packaging_id = False


    @api.onchange('discount')
    def _onchange_discount_sale_line(self):
        date_today = date.today()
        for sale_line in self:
            if not self.env.user.has_group('cha_sarya_sales.can_override_sales_discount'):
                pricelist = sale_line.order_id.pricelist_id

                records = sale_line.order_id.pricelist_id.item_ids.filtered(lambda
                                                    l: l.product_tmpl_id == sale_line.product_id.product_tmpl_id and \
                                                       l.packging_id == sale_line.product_packaging_id and \
                                                       l.active == True)
                max_discount = 0
                for record in records:
                    if record.date_start and record.date_end:
                        if record.date_start.date() <= date_today <= record.date_end.date():
                            max_discount = record.price_discount
                            break
                        else:
                            continue
                    else:
                        max_discount = record.price_discount

                if sale_line.discount > max_discount:
                    sale_line.discount = 0
                    res = {}
                    res['warning'] = {'title': _('Warning'), 'message': _('You are not allowed to give this discount.')}
                    return res


class StockMove(models.Model):

    _inherit = 'stock.move'

    def _set_date_deadline(self, new_deadline):
        if new_deadline:
            return super(StockMove, self)._set_date_deadline(new_deadline)



