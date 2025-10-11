
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, time
from dateutil.relativedelta import relativedelta

PURCHASE_REQUISITION_STATES = [
    ('draft', 'Draft'),
    ('to_approve', 'To Approve'),
    ('ongoing', 'Ongoing'),
    ('in_progress', 'Confirmed'),
    ('open', 'Bid Selection'),
    ('done', 'Closed'),
    ('cancel', 'Cancelled')
]
class SRYPurchaseAgreement(models.Model):
    _inherit = 'purchase.requisition'

    def _get_type_id(self):
        return self.env['purchase.requisition.type'].search([('name', '=', 'Blanket Order')], limit=1)


    state_blanket_order = fields.Selection(PURCHASE_REQUISITION_STATES, compute='_set_state')
    state = fields.Selection(PURCHASE_REQUISITION_STATES, 'Status', tracking=True, required=True, copy=False, default='draft')
    type_id = fields.Many2one('purchase.requisition.type', string="Order Type", required=True, default=_get_type_id)
    forcast_attachment = fields.Binary(string='Forcast Attachment')
    forcast_attachment_filename = fields.Char(string='Forcast Attachment File Name', store=True, copy=False)
    user_id = fields.Many2one('res.users', string='Responsible Person', default=lambda self: self.env.user, check_company=True)
    total_amount = fields.Float(compute='_compute_total_amount', string='Total Amount')

    amount_in_words = fields.Char(required=False, compute="_amount_in_word")

    def _amount_in_word(self):
        for rec in self:
            rec.amount_in_words = str(rec.currency_id.amount_to_text(rec.total_amount)).upper()


    def _compute_total_amount(self):
        for requisition in self:
            total_amount = 0
            for line in requisition.line_ids:
                total_amount = total_amount + (line.product_packaging_qty * line.pkg_unit_price)

            requisition.total_amount = total_amount


    @api.model
    def create(self, values):
        res = super(SRYPurchaseAgreement, self).create(values)
        res.name = self.env['ir.sequence'].next_by_code('purchase.requisition.blanket.order')
        return res

    def send_finance_approval(self):
        for req in self:
            req.state = 'to_approve'
            req.send_notification_to_accounts_to_approve()

    def send_notification_to_accounts_to_approve(self):
        mail_content = " Hello,"
        mail_content = "%s<br>Please approve Blanket Order: %s, Vendor : %s" % (mail_content, self.name, self.vendor_id.name)
        users = self.env.ref('kg_sarya_pur_agreement.can_approve_blanket_order').users
        email_to = ""
        for usr in users:
            if usr.partner_id.email:
                if not email_to:
                    email_to = usr.partner_id.email
                else:
                    email_to = email_to + ', ' + usr.partner_id.email
        main_content = {
            'subject': _('Blanket Order to Approve'),
            'author_id': self.env.user.partner_id.id,
            'body_html': mail_content,
            'email_to': email_to,
        }
        self.env['mail.mail'].sudo().create(main_content).send()


    def approve_blanket_order(self):
        for req in self:
            req.ordering_date = fields.Date.today()
            req.date_end =  fields.Date.today() + relativedelta(month=2)
            req.state = 'ongoing'
            req.send_approved_notification()

    def send_approved_notification(self):
        mail_content = " Hello,"
        mail_content = "%s<br>Order: %s for Vendor : %s is approved" % (mail_content, self.name, self.vendor_id.name)
        users = self.env.ref('kg_sarya_pur_agreement.can_approve_blanket_order').users
        email_to = self.user_id.partner_id.email
        main_content = {
            'subject': _('Blanket Order to Approved'),
            'author_id': self.env.user.partner_id.id,
            'body_html': mail_content,
            'email_to': email_to,
        }
        self.env['mail.mail'].sudo().create(main_content).send()


class PurchaseAgreement(models.Model):
    _inherit = 'purchase.requisition.line'

    product_packaging_id = fields.Many2one('product.packaging', string='Packaging', domain="[('purchase', '=', True), ('product_id', '=', product_id)]", check_company=True)
    product_packaging_qty = fields.Float('Qty', help="Packaging quantity")
    pkg_unit_price = fields.Float(string="Packaging unit price")
    pkg_qty_ordered = fields.Float(string="Ordered Package quantity", compute="compute_package_ordered_qty")
    qty_ordered = fields.Float(string='Ordered Quantities', compute='compute_ordered_qty')
    total_amount = fields.Float(string='Total Amount', compute='compute_total_amount')

    def compute_total_amount(self):
        for line in self:
            line.total_amount = line.product_packaging_qty * line.pkg_unit_price

    def compute_ordered_qty(self):
        for line in self:
            #line_found = set()
            total = 0.0
            for po in line.requisition_id.purchase_ids.filtered(
                    lambda purchase_order: purchase_order.state != 'cancel'):
                for po_line in po.order_line.filtered(lambda order_line: order_line.product_id == line.product_id):
                    if po_line.product_uom != line.product_uom_id:
                        total += po_line.product_uom._compute_quantity(po_line.product_qty, line.product_uom_id)
                    else:
                        total += po_line.product_qty

            line.qty_ordered = total
            # if line.product_id not in line_found:
            #     line.qty_ordered = total
            #     line_found.add(line.product_id)
            # else:
            #     line.qty_ordered = 0


    def compute_package_ordered_qty(self):
        for line in self:
            if line.qty_ordered != 0.00:
                line.pkg_qty_ordered = line.qty_ordered/line.product_packaging_id.qty
            else:
                line.pkg_qty_ordered = 0.00

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_po_id
            self.product_qty = 0
            self.product_packaging_qty = 0
            self.product_packaging_id = False
        if not self.schedule_date:
            self.schedule_date = self.requisition_id.schedule_date

    @api.onchange('product_packaging_id','product_packaging_qty')
    def _onchange_product_packaging_id(self):
        if self.product_packaging_id:
            self.product_qty = self.product_packaging_id.qty * self.product_packaging_qty
            if self.product_id and self.product_packaging_id:
                vendor_pl = self.env['product.supplierinfo'].search([('product_tmpl_id','=',self.product_id.product_tmpl_id.id),('package_id','=',self.product_packaging_id.id)], limit=1)
                self.pkg_unit_price = vendor_pl.package_price

    @api.onchange('pkg_unit_price')
    def _onchange_pkg_unit_price(self):
        if self.pkg_unit_price and self.product_packaging_id:
            self.price_unit = self.pkg_unit_price/self.product_packaging_id.qty

    def _prepare_purchase_order_line_sarya(self, product_qty=0.0, taxes_ids=False):
        self.ensure_one()
        requisition = self.requisition_id

        if requisition.schedule_date:
            date_planned = datetime.combine(requisition.schedule_date, time.min)
        else:
            date_planned = datetime.now()

        price_unit = 0
        supplier_info = self.env['product.supplierinfo'].search([('partner_id', '=', self.requisition_id.vendor_id.id),
                             ('product_tmpl_id', '=', self.product_id.product_tmpl_id.id),
                             ('package_id', '=', self.product_packaging_id.id)], limit=1)

        if supplier_info:
            price_unit = supplier_info.package_price

        pkg_unit_price = price_unit
        price_unit = price_unit / self.product_packaging_id.qty
        line_pkg_status = True

        return {
            'name': self.product_packaging_id.description,
            'product_id': self.product_id.id,
            'product_uom': self.product_id.uom_po_id.id,
            'product_qty': product_qty * self.product_packaging_id.qty,
            'price_unit': price_unit,
            'taxes_id': [(6, 0, taxes_ids)],
            'date_planned': date_planned,
            #'account_analytic_id': self.account_analytic_id.id,
            #'analytic_tag_ids': self.analytic_tag_ids.ids,
            'product_packaging_id':self.product_packaging_id.id,
            'product_packaging_qty': product_qty,
            'pkg_unit_price': pkg_unit_price,
            'line_pkg_status' : line_pkg_status
        }