# -*- coding: utf-8 -*-

from odoo import models, api, fields
from odoo.tools.misc import get_lang
from odoo.addons import decimal_precision as dp

class Attachments(models.Model):
    _inherit = 'partner.attachments'

    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')

    @api.model
    def create(self, vals):
        res = super(Attachments, self).create(vals)
        for doc in res:
            if doc.purchase_order_id:
                doc.purchase_order_id.update_shipping_doc_status()
        return res

    def write(self, values):

        document_count = 0
        for doc in self:
            document_count += len(doc.doc_attachment_partner)

        res = super(Attachments, self).write(values)

        updated_doc_count = 0
        for doc in self:
            if doc.purchase_order_id:
                doc.purchase_order_id.update_shipping_doc_status()
            updated_doc_count += len(doc.doc_attachment_partner)

        if updated_doc_count < document_count:
            for doc in self:
                if doc.purchase_order_id:
                    msg = "Attachment is deleted from the %s" % doc.document_name
                    doc.purchase_order_id.message_post(body=msg)

        if updated_doc_count > document_count:
            for doc in self:
                if doc.purchase_order_id:
                    msg = "Attachment has been added to the %s" % doc.document_name
                    doc.purchase_order_id.message_post(body=msg)

        return res

    def unlink(self):
        purchase_order_id = []
        for doc in self:
            if doc.purchase_order_id:
                purchase_order_id.append(doc.purchase_order_id)
        res = super(Attachments, self).unlink()
        for po in purchase_order_id:
            po.update_shipping_doc_status()
        return res

class Purchase(models.Model):
    _inherit = 'purchase.order'

    po_type = fields.Selection(string='PO Type', selection=[('import', 'Import'), ('local', 'Local')], default='import')
    stock_type = fields.Selection(string='Inventory Type', selection=[('inventory', 'Inventory'), ('non_inventory', 'Non Inventory')],
                                  default='inventory')
    is_closed = fields.Boolean(string="Is Closed", default=False, copy=False)
    is_pi_qty_entered = fields.Boolean("PI Quantity Entered?", copy=False)

    receiving_status = fields.Selection(string='Receiving Status',
            selection=[('not_received', 'No items received'),
                       ('partial', 'Items are partially received'),
                       ('complete', 'Items are fully received')], default="not_received", copy=False)

    shipping_status = fields.Selection(string='Shipping Status',
                                        selection=[('not_shipped', 'No items are shipped'),
                                                   ('partial', 'Items are partially shipped'),
                                                   ('complete', 'Items are fully shipped')], default="not_shipped", copy=False)

    container_type = fields.Selection(string='Container Type',
            selection=[('reefer_chilled', 'Reefer Chilled'),
                       ('reefer_frozen', 'Reefer Frozen'),
                       ('dry', 'Dry'), ('air', 'Air')], copy=False)

    container_volume = fields.Selection(string='Container Volume',
                                      selection=[('40_feet', '40 Feet'), ('20_feet', '20 Feet'), ('dry', 'Other')], copy=False)


    finance_waiting_approval = fields.Selection(string="Waiting Approval",
                                    selection=[('new_po', 'New PO'),
                                               ('pi_change', 'PI Qty Change')], copy=False)

    amount_after_discount = fields.Float("Amount After Disc", compute='_compute_discounts_from_vendor')

    is_document_request_sent_to_vendors = fields.Boolean("Is document request sent to Vendors")
    is_shipping_documents_uploaded = fields.Boolean("Is Shipping Documents Fully Uploaded")
    last_document_reminder_sent_to_vendor = fields.Date("Last Document reminder sent to vendor")
    shipping_documents = fields.One2many('partner.attachments', 'purchase_order_id', string="Shipping Documents")


    def _compute_discounts_from_vendor(self):
        for po in self:
            amount_after_discount = 0
            for po_line in po.order_line:
                amount_after_discount += po_line.amount_after_discount
            po.amount_after_discount = amount_after_discount

    def update_shipping_status(self):
        #This method called form shipment advice to update shipping status on po
        for po in self:

            #Intialising shipping status as completed and item not shipped as true
            #
            #If any shipment.allocation is found items_not_shipped changed to False,
            #because some item is already on shipment advice
            #
            #If any pending_qty_to_ship is greater than zero  then shipping_status is turned to partial

            shipping_status = 'complete'
            items_not_shipped = True
            for po_line in po.order_line:
                allocation = self.env['lpo.wise.shipment.allocation'].search([
                    ('purchase_line_id', '=', po_line.id)])
                if allocation:
                    items_not_shipped = False
                    allocation_qty = 0
                    for alloc in allocation:
                        allocation_qty += alloc.shipment_advice_line_qty
                    pending_qty_to_ship = po_line.product_packaging_qty - allocation_qty
                    if pending_qty_to_ship > 0:
                        shipping_status = 'partial'
            if items_not_shipped:
                po.shipping_status = 'not_shipped'
            else:
                po.shipping_status = shipping_status


    def update_receiving_status(self):
        for po in self:
            receiving_status = 'complete'
            check_not_received = True
            for po_line in po.order_line:
                if po_line.product_uom_qty != po_line.qty_received:
                    receiving_status = 'partial'

                if po_line.qty_received > 0:
                    check_not_received = False

            if check_not_received:
                po.receiving_status = 'not_received'
            else:
                po.receiving_status = receiving_status


    def _create_picking(self):
        if self.company_id.company_type == 'retail':
            return super(Purchase, self)._create_picking()
        elif self.company_id.company_type == 'distribution':
            """Should not allow purchase order creating picking as it will be created while confirming the shipment."""
            return False

    def _add_supplier_to_product(self):
        """Should not allow purchase order creating supplier in the products as we do it manually."""
        return False

    def action_close_po(self):
        for rec in self:
            if rec.state in ['purchase', 'done']:
                rec.is_closed = True


    def button_approve(self, force=False):
        res = super(Purchase, self).button_approve()

        for po in self:
           for po_line in po.order_line:
               po_line.approved_po_qty = po_line.product_packaging_qty
               po_line.pi_qty = po_line.product_packaging_qty
               po_line.pi_foc_qty = po_line.foc_qty

        return res


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    foc_qty = fields.Float("FOC Qty")
    pi_qty = fields.Float(string="PI Qty", copy=False)
    pi_foc_qty = fields.Float("PI FOC Qty", copy=False)
    approved_po_qty = fields.Float(string="Approved PO Qty", copy=False)
    discount_one = fields.Float("Disc 1", compute='_compute_discounts_from_vendor')
    discount_two = fields.Float("Disc 2", compute='_compute_discounts_from_vendor')
    total_discount = fields.Float("Total Disc", compute='_compute_discounts_from_vendor')
    amount_after_discount = fields.Float("Amount After Disc", compute='_compute_discounts_from_vendor')


    def _compute_discounts_from_vendor(self):

        for po_line in self:
            discount_one = 0
            discount_two = 0
            total_discount = 0
            amount_after_discount = 0

            total = po_line.price_subtotal
            suppiler_info = self.env['product.supplierinfo'].search([('partner_id', '=', po_line.order_id.partner_id.id),
                                                                     ('product_tmpl_id', '=', po_line.product_id.product_tmpl_id.id)])

            if suppiler_info:
                disc1 = suppiler_info.discount_1
                disc2 = suppiler_info.discount_2
                discount_sum = disc1 + disc2

                discount_one = total * disc1
                discount_two = total * disc2
                total_discount = total * discount_sum
                amount_after_discount = total - total_discount

            po_line.discount_one = discount_one
            po_line.discount_two = discount_two
            po_line.total_discount = total_discount
            po_line.amount_after_discount = amount_after_discount


    @api.onchange('pi_qty')
    def _onchange_pi_qty(self):

        for po_line in self:
            print("_onchange_pi_qty", po_line)
            po_line.product_packaging_qty = po_line.pi_qty


    def _product_id_change(self):
        """autofill product package with the vendor package set in the product."""
        res = super(PurchaseOrderLine, self)._product_id_change()
        seller_ids = self.product_id.seller_ids \
            .filtered(
            lambda r: r.partner_id == self.order_id.partner_id and (not r.product_id or r.product_id == self.product_id)) \
            .sorted(key=lambda r: r.min_qty)
        self.update({
            'product_packaging_id': seller_ids[0].package_id.id if seller_ids else False,
        })
        return res

    def _get_product_purchase_description(self, product_lang):
        """
        by-default, Odoo takes product description as the orderline name,
        we change it to product package description
        """
        self.ensure_one()
        name = super(PurchaseOrderLine, self)._get_product_purchase_description(product_lang)
        if self.product_packaging_id:
            name = product_lang.name_get_with_package(self.product_packaging_id)
            if product_lang.description_purchase:
                name += '\n' + product_lang.description_purchase
        return name

    @api.onchange('product_packaging_id')
    def _onchange_product_packaging_id(self):
        res = super(PurchaseOrderLine, self)._onchange_product_packaging_id()
        product_lang = self.product_id.with_context(
            lang=get_lang(self.env, self.partner_id.lang).code,
            partner_id=self.partner_id.id,
            company_id=self.company_id.id,
        )
        #self._get_product_purchase_description(product_lang)
        return res
