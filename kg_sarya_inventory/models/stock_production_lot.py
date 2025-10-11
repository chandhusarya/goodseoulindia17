# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import pytz
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons import decimal_precision as dp
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import logging
from odoo.osv.expression import AND, OR

from twilio.rest import Client
import json

_logger = logging.getLogger(__name__)


class ProductionLot(models.Model):
    _inherit = 'stock.lot'

    available_qty = fields.Float('Packaging Quantity', compute='_item_qty', store=True)
    primary_packaging_id = fields.Many2one('product.packaging', 'Primary Package', compute='_update_package')
    active = fields.Boolean('Active', default=True)

    fixed_discount = fields.Float(string="Fixed Discount")
    additional_discount = fields.Float(string="Additional Discount")
    final_cost_after_discount = fields.Float(string="After Discount Cost")


    def _compute_purchase_cost(self):
        for lot in self:
            purchase_cost = 0
            landed_cost = 0
            final_cost = 0

            stock_valuation = self.env['stock.valuation.layer'].sudo().with_context(active_test=False).search([
                ('product_id', '=', lot.product_id.id),
                ('company_id', '=', lot.company_id.id),
                ('lot_id', '=', lot.id)], order='create_date, id', limit=10)
            if stock_valuation:
                #purchase_stock_valuation = stock_valuation[0]

                value = 0
                quantity = 0
                purchase_candidates = []
                for purchase_stock_valuation in stock_valuation:
                    if purchase_stock_valuation.stock_move_id and purchase_stock_valuation.stock_move_id.origin \
                            and 'P0' in purchase_stock_valuation.stock_move_id.origin and not purchase_stock_valuation.stock_landed_cost_id:

                        value += purchase_stock_valuation.value
                        quantity += purchase_stock_valuation.quantity
                        purchase_candidates.append(purchase_stock_valuation.id)

                    elif purchase_stock_valuation.stock_move_id and purchase_stock_valuation.stock_move_id.origin \
                            and 'LP/' in purchase_stock_valuation.stock_move_id.origin and not purchase_stock_valuation.stock_landed_cost_id:

                        value += purchase_stock_valuation.value
                        quantity += purchase_stock_valuation.quantity
                        purchase_candidates.append(purchase_stock_valuation.id)

                if not purchase_candidates:
                    #consider Manufactured also
                    for purchase_stock_valuation in stock_valuation:
                        if purchase_stock_valuation.stock_move_id and purchase_stock_valuation.stock_move_id.origin \
                                and 'PF/MO' in purchase_stock_valuation.stock_move_id.origin and not purchase_stock_valuation.stock_landed_cost_id \
                                and purchase_stock_valuation.quantity > 0:
                            value += purchase_stock_valuation.value
                            quantity += purchase_stock_valuation.quantity
                            purchase_candidates.append(purchase_stock_valuation.id)




                if quantity > 0:
                    purchase_cost = value/quantity
                    landed_cost_value = 0

                    domain = [
                        ('company_id', '=', self.company_id.id),
                        ('product_id', '=', lot.product_id.id),
                        ('lot_id', '=', lot.id),
                        ('quantity', '=', 0),
                        ('unit_cost', '=', 0),
                        #('create_date', '>=', purchase_stock_valuation.create_date),
                        ('id', 'not in', purchase_candidates),
                        ('stock_landed_cost_id', '!=', False)
                    ]
                    all_candidates = self.env['stock.valuation.layer'].sudo().search(domain)
                    for candidate in all_candidates:
                        value += candidate.value
                        landed_cost_value += candidate.value

                    landed_cost = landed_cost_value / quantity
                    final_cost = value / quantity

            lot.purchase_cost = purchase_cost
            lot.landed_cost = landed_cost
            lot.final_cost = final_cost


    purchase_cost = fields.Float(string="Purchase Cost", compute='_compute_purchase_cost', digits=(16, 7))
    landed_cost = fields.Float(string="Landed Cost", compute='_compute_purchase_cost', digits=(16, 7))
    final_cost = fields.Float(string="Final Cost (Po cost + LC)", compute='_compute_purchase_cost', digits=(16, 7))

    @api.depends('expiration_date', 'name')
    def _compute_display_name(self):
        res = []
        user_tz = self.env.context.get('tz', 'Asia/Dubai')
        for rec in self:
            name = "%s" % rec.name
            if rec.expiration_date:
                expiry_date = pytz.UTC.localize(rec.expiration_date)
                expiry_date = expiry_date.astimezone(pytz.timezone(user_tz))
                name = "%s [%s]" % (rec.name, expiry_date.strftime('%d-%m-%Y'))
            rec.display_name = name


    @api.depends('quant_ids', 'quant_ids.quantity')
    def _update_package(self):
        for rec in self:
            if rec.product_id:
                primary_packaging_id = self.env['product.packaging'].search(
                    [('product_id', '=', rec.product_id.id), ('primary_unit', '=', True)])
                rec.primary_packaging_id = primary_packaging_id.id

    @api.depends('quant_ids', 'quant_ids.quantity', 'primary_packaging_id')
    def _item_qty(self):
        for lot in self:
            # We only care for the quants in internal or transit locations.
            quants = lot.quant_ids.filtered(lambda q: q.location_id.usage == 'internal' or (
                    q.location_id.usage == 'transit' and q.location_id.company_id))
            available_qty = sum(quants.mapped('quantity'))
            lot.available_qty = round(available_qty / lot.primary_packaging_id.qty, 3) if lot.product_id and lot.primary_packaging_id.qty else 0

    def action_archive_lot(self):
        return True
        cron_start_date = datetime.now()
        lots = self.env['stock.lot'].search([('active', '=', True)])
        limit_lots = lots.filtered(lambda x: (
                x.product_qty <= 0 or x.expiration_date < datetime.today()) if x.expiration_date else x.product_qty <= 0)
        for rec in limit_lots:
            rec.active = False
        _logger.info("Archive Lot : Cron duration = %d seconds" % (
            (datetime.now() - cron_start_date).total_seconds()))

    # @api.constrains('available_qty', )
    # def _check_product_quantity(self):
    #     for lot in self:
    #         if lot.available_qty and lot.product_qty and lot.active:
    #             if lot.available_qty < 0:
    #                 raise ValidationError(
    #                     _("This operation can not be completed as the lot quantity is less than the required quantity"))

    def _alert_date_exceeded(self):
        """Log an activity on internally stored lots whose alert_date has been reached.

        No further activity will be generated on lots whose alert_date
        has already been reached (even if the alert_date is changed).
        """
        alert_lots = self.env['stock.lot'].search([
            ('alert_date', '<=', fields.Date.today()),
            ('product_expiry_reminded', '=', False)])

        lot_stock_quants = self.env['stock.quant'].search([
            ('lot_id', 'in', alert_lots.ids),
            ('quantity', '>', 0),
            ('location_id.usage', '=', 'internal')])
        alert_lots = lot_stock_quants.mapped('lot_id')
        for lot in alert_lots:
            lot.activity_schedule(
                'product_expiry.mail_activity_type_alert_date_reached',
                user_id=lot.product_id.responsible_id.id or SUPERUSER_ID,
                note=_("The alert date has been reached for this lot/serial number")
            )
        if alert_lots:
            user_ids = self.env.user.company_id.lot_mail_users_ids
            map_users_mail = user_ids.mapped('login')
            users_mail = ",".join(map_users_mail)
            email_values = {
                # 'attachment_ids': False,
                'email_to': users_mail,
                # 'subject': subject,
                # 'email_from': self.env.user.email_formatted,
                # 'author_id': self.env.user.partner_id.id,
            }
            local_context = self.env.context.copy()
            local_context.update({
                'lots': alert_lots
            })
            mail_template = self.env.ref('kg_sarya_inventory.id_lot_alert_email_template')
            mail_template.sudo().with_context(local_context).send_mail(self.id, force_send=True,
                                                                       email_values=email_values)
        alert_lots.write({
            'product_expiry_reminded': True
        })

class StockPickingInh(models.Model):
    _inherit = "stock.picking"

    is_stock_confirmed = fields.Boolean("Is stock confirmed", tracking=True, default=False)

    # Auto assign lot numbers
    def button_validate(self):
        pickings_using_lots = self.filtered(
            lambda p: p.picking_type_id.use_create_lots or p.picking_type_id.use_existing_lots)
        if pickings_using_lots:
            no_quantities_done_ids = set()
            separate_pickings = True
            lines_to_check = pickings_using_lots._get_lot_move_lines_for_sanity_check(no_quantities_done_ids,
                                                                                      separate_pickings)
            for line in lines_to_check:
                if not line.lot_name and not line.lot_id:
                    line.lot_name = self.env['ir.sequence'].next_by_code('auto.lot.number')

        res = super(StockPickingInh, self).button_validate()

        for picking in self:
            if picking.picking_type_id.code == 'outgoing' and 'SARYA DISTRIBUTION' in picking.company_id.name:
                users = self.env.ref('cha_sarya_sales.delivery_order_validation_notification_notification').users
                employee_ids = []
                for user in users:
                    employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
                    if employee:
                        employee_ids.append(employee.id)
                    else:
                        raise UserError(_("User %s does not have an employee record.") % user.name)
                if employee_ids:
                    employees = self.env['hr.employee'].browse(employee_ids)
                    for employee in employees:
                        message = "Hi %s, Delivery Order %s is validated" % (
                        employee.name, picking.name)
                        subject = "Delivery Confirmation Notification for %s" % picking.name
                        button_url = "#id=%s&cids=1&menu_id=280&action=416&model=stock.picking&view_type=form" % (
                            str(picking.id))
                        self.send_notification(employees, message, subject, button_url)
        return res


    def send_notification(self, employee_ids, message, subject, button_url):

        for employee_id in employee_ids:
            # Email notification
            mail_content = "Dear " + str(employee_id.name)
            print("message =========>> ", message)
            mail_content += "<br/><br/>" + message
            main_content = {
                "subject": subject,
                "body_html": mail_content,
                "email_to": employee_id.work_email,
            }
            self.env['mail.mail'].sudo().create(main_content).send()

            #Whatsapp message
            account_sid = self.env['ir.config_parameter'].sudo().get_param('twilio.account_sid', False)
            auth_token = self.env['ir.config_parameter'].sudo().get_param('twilio.auth_token', False)
            from_number = self.env['ir.config_parameter'].sudo().get_param('twilio.from', False)
            if employee_id.whatsapp_number:
                to_number = employee_id.whatsapp_number
            else:
                # Fallback to mobile or work phone if whatsapp number is not available
                to_number = employee_id.mobile_phone and employee_id.mobile_phone or employee_id.work_phone

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


    def confirm_stock_entry(self):
        for picking in self:
            picking.is_stock_confirmed = True

            subject = '%s :  %s Validation Request' % (picking.picking_type_id.name, picking.name)
            mail_content = " Hello,<br> Please Validate Request %s : %s : " % (picking.picking_type_id.name, picking.name)

            users = self.env.ref('kg_sarya_inventory.can_view_validate_picking').users
            email_to = ""
            for usr in users:
                if usr.partner_id.email:
                    if not email_to:
                        email_to = usr.partner_id.email
                    else:
                        email_to = email_to + ', ' + usr.partner_id.email

            main_content = {
                'subject': subject,
                'author_id': self.env.user.partner_id.id,
                'body_html': mail_content,
                'email_to': email_to,
            }
            self.env['mail.mail'].sudo().create(main_content).send()




class StockMoveLineInheritTree(models.Model):
    _inherit = 'stock.move.line'

    product_packaging_id = fields.Many2one('product.packaging', string="Packaging",
                                           related='move_id.product_packaging_id', store=True)
    pkg_demand = fields.Float(string="Pkg Demand", related='move_id.pkg_demand', store=True)


    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            if 'lot_id' not in val:
                if self.company_id.company_type == 'retail':
                    pass
                elif self.company_id.company_type == 'distribution':
                    pass
        return super(StockMoveLineInheritTree, self).create(vals_list)


    def write(self, vals):
        if 'lot_id' in vals or 'lot_name' in vals:
            if self.company_id.company_type == 'retail':
                pass
            elif self.company_id.company_type == 'distribution':
                pass
        res = super(StockMoveLineInheritTree, self).write(vals)
        return res

class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    primary_packaging_id = fields.Many2one('product.packaging', 'Primary Package', compute='_find_primary_package')

    def _find_primary_package(self):
        for mrp in self:
            primary_packaging_id = False
            for pack in mrp.product_id.packaging_ids:
                if pack.primary_unit:
                    primary_packaging_id = pack.id
            mrp.primary_packaging_id = primary_packaging_id


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    primary_packaging_id = fields.Many2one('product.packaging', 'Primary Package', compute='_find_primary_package')

    def _find_primary_package(self):
        for mrp in self:
            primary_packaging_id = False
            for pack in mrp.product_id.packaging_ids:
                if pack.primary_unit:
                    primary_packaging_id = pack.id
            mrp.primary_packaging_id = primary_packaging_id

    @api.constrains('active', 'product_id', 'product_tmpl_id', 'bom_line_ids')
    def _check_bom_cycle(self):
        subcomponents_dict = dict()

        def _check_cycle(components, finished_products):
            """
            Check whether the components are part of the finished products (-> cycle). Then, if
            these components have a BoM, repeat the operation with the subcomponents (recursion).
            The method will return the list of product variants that creates the cycle
            """
            products_to_find = self.env['product.product']

            for component in components:
                if component in finished_products and False:
                    names = finished_products.mapped('display_name')
                    raise ValidationError(_(
                        "The current configuration is incorrect because it would create a cycle between these products: %s.",
                        ', '.join(names)))

                if component not in finished_products and component not in subcomponents_dict:
                    products_to_find |= component

            bom_find_result = self._bom_find(products_to_find)
            for component in components:
                if component not in subcomponents_dict:
                    bom = bom_find_result[component]
                    subcomponents = bom.bom_line_ids.filtered(lambda l: not l._skip_bom_line(component)).product_id
                    subcomponents_dict[component] = subcomponents
                subcomponents = subcomponents_dict[component]
                if subcomponents:
                    _check_cycle(subcomponents, finished_products | component)

        boms_to_check = self
        domain = []
        for product in self.bom_line_ids.product_id:
            domain = OR([domain, self._bom_find_domain(product)])
        if domain:
            boms_to_check |= self.env['mrp.bom'].search(domain)

        for bom in boms_to_check:
            if not bom.active:
                continue
            finished_products = bom.product_id or bom.product_tmpl_id.product_variant_ids
            if bom.bom_line_ids.bom_product_template_attribute_value_ids:
                grouped_by_components = defaultdict(lambda: self.env['product.product'])
                for finished in finished_products:
                    components = bom.bom_line_ids.filtered(lambda l: not l._skip_bom_line(finished)).product_id
                    grouped_by_components[components] |= finished
                for components, finished in grouped_by_components.items():
                    _check_cycle(components, finished)
            else:
                _check_cycle(bom.bom_line_ids.product_id, finished_products)

class MrpProduction(models.Model):
    """ Manufacturing Orders """
    _inherit = 'mrp.production'

    @api.onchange('product_id', 'move_raw_ids')
    def _onchange_product_id(self):
        for move in self.move_raw_ids:
            if self.product_id == move.product_id and False:
                message = _("The component %s should not be the same as the product to produce.",
                            self.product_id.display_name)
                self.move_raw_ids = self.move_raw_ids - move
                return {'warning': {'title': _('Warning'), 'message': message}}

    primary_packaging_id = fields.Many2one('product.packaging', 'Primary Package', compute='_find_primary_package')

    def _find_primary_package(self):
        for mrp in self:
            primary_packaging_id = False
            for pack in mrp.product_id.packaging_ids:
                if pack.primary_unit:
                    primary_packaging_id = pack.id
            mrp.primary_packaging_id = primary_packaging_id
