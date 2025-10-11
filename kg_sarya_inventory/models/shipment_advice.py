# -*- coding: utf-8 -*-

from odoo import models, fields, _, api, SUPERUSER_ID
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_round, float_is_zero, groupby
from datetime import date

from datetime import datetime, timedelta,date
import time


class ShipmentAdvice(models.Model):
    _name = 'shipment.advice'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Shipment Advice'
    _rec_name = 'name'
    _order = 'name desc, id desc'

    name = fields.Char(string='Name', required=True, readonly=True, default=lambda self: _('New'), copy=False)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
                                 default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', 'Responsible', copy=False, default=lambda self: self.env.user, required=True,
                              tracking=True)
    state = fields.Selection(
        string='Status',
        selection=[
            ('draft', 'Draft'),
            ('waiting_finance_approval', 'Waiting Finance Approval'),
            ('finance_approved', 'Finance Approved'),
            ('inspection', 'Inspection'),
            ('open', 'Open'),
            ('done', 'Close'),
            ('item_in_receiving', 'Item in Inspection Location'),
            ('item_received', 'Received'),
            ('cancel', 'Cancelled'),
        ],
        required=True, tracking=True, default='draft')

    inspection_method = fields.Selection(string='Inspection method',
        selection=[('inspection_at_port', 'Inspection at port'),
                   ('inspection_at_warehouse', 'Inspection at warehouse')])

    is_on_inspection = fields.Boolean(string="Is on Inspection", default=False)

    is_full_override_allowed = fields.Boolean(string="Is full override allowed?", default=False)

    shipment_no = fields.Char('Invoice No', copy=False, tracking=True)
    container_no = fields.Char('Container No.', copy=False, tracking=True)
    bill_no = fields.Char('BL No.', copy=False, tracking=True)
    zdlm = fields.Char('ZDLM', copy=False, tracking=True)
    boe_number = fields.Char('BOE', copy=False, tracking=True)
    departure_date = fields.Date('Departure Date', tracking=True)
    arrival_date = fields.Date('Arrival Date', tracking=True)
    arrival_date_wh = fields.Date('Arrival Date Warehouse', tracking=True)
    expected_date = fields.Date('Expected Date', tracking=True)
    notes = fields.Text('Notes')
    attachment_ids = fields.One2many('partner.attachments', 'shipment_id', string='Attachments', tracking=True)
    shipment_lines = fields.One2many(comodel_name='shipment.advice.line', inverse_name='shipment_id',
                                     string='Shipment Products', required=False)
    shipment_summary_lines = fields.One2many(comodel_name='shipment.advice.summary', inverse_name='shipment_id',
                                             string='Shipment Summary', required=False, tracking=True)

    lpo_wise_allocation = fields.One2many('lpo.wise.shipment.allocation', 'shipment_advice_id', string="LPO wise allocation")

    shipment_summary_generated = fields.Boolean("Is shipment summary generated?")

    vendor_id = fields.Many2one('res.partner', string="Vendor")
    next_id = fields.Integer()
    is_inspected = fields.Boolean(string="Is inspected", default=False)
    invoice_status = fields.Boolean(default=False)
    picking_count = fields.Integer('Receipt Count', compute='_compute_count')
    purchase_count = fields.Integer('PO Count', compute='_compute_count')
    invoice_count = fields.Integer('Invoice Count', compute='_compute_count')
    discount_count = fields.Integer('Discount Count', compute='_compute_count')

    invoice_id = fields.Many2one('account.move', string='Invoice ID')

    invoice_ids = fields.Many2many('account.move', 'shipment_advice_invoices', "shipment_advice_id", "move_id",
                                   copy=False, string="Invoices")

    entry_ids = fields.One2many('account.move', 'shipment_id', string="Entry")

    is_invoiced = fields.Selection([('not_invoiced', 'Not Invoiced'), ('invoiced', 'Invoiced')],
                                      string='Invoiced or Not Invoiced', store=True, default='not_invoiced')

    landed_cost_to_apply = fields.One2many('shipment.advice.landed.cost', 'shipment_advice_id', string="Landed Cost")

    inspection_date = fields.Date('Inspection Date', tracking=True)

    purchase_id = fields.Many2one('purchase.order', 'Purchase', ondelete='cascade', copy=False,
        domain="[('state', 'in', ('purchase', 'done')), "
               "('stock_type', '=', 'inventory'), "
               "('partner_id', '=', vendor_id), "
               "('is_closed', '=', False),"
               "('is_pi_qty_entered', '=', True)]")

    purchase_ids = fields.Many2many('purchase.order',
                                    'sarya_shipment_advice_purchase_order',
                                    "shipment_advice_id", "purchase_id",
                                    required=True, copy=False,
                                    domain="[('state', 'in', ('purchase', 'done')), "
                                         "('stock_type', '=', 'inventory'), "
                                         "('partner_id', '=', vendor_id), "
                                         "('shipping_status', '!=', 'complete'),"
                                         "('finance_waiting_approval', '=', False),"
                                         "('is_pi_qty_entered', '=', True)]")


    is_ci_not_matching = fields.Boolean("Commercial invoicing not matching?")
    ci_not_matching_reason = fields.Char("Commercial invoicing not matching Reason")

    inspection_location = fields.Many2one('stock.location', string='Inspection Location')
    scrap_location = fields.Many2one('stock.location', string='Scrap Location')

    main_stock_location = fields.Many2one('stock.location', string='Main Stock Location')

    is_scrapping_completed = fields.Boolean("Is scrapping completed?", tracking=True)

    inspection_status = fields.Selection(
        [('not_inspected', 'Not Inspected'), ('inspecting', 'Inspecting'), ('inspected', 'Inspected')],
        default='not_inspected')

    is_inspection_override_visible = fields.Boolean('Is Inspection Override Visible', compute='_compute_inspection_override')

    debit_acc_additional_disc = fields.Many2one('account.account', string="Debit Account for Additional Discount")
    credit_acc_additional_disc = fields.Many2one('account.account', string="Credit Account for Additional Discount")
    journal_additional_disc = fields.Many2one('account.journal', string="Journal for Additional Discount")

    additional_discounts = fields.Many2many('account.move',
                                    'shipment_advice_additional_discount',
                                    "shipment_advice_id", "move_id", copy=False, string="Additional Discounts")

    clearing_agent = fields.Many2one('res.partner', string="Clearing Agent")
    is_docs_send_to_agent = fields.Boolean("Is documents send to clearing Agent")

    grn_entry_status = fields.Selection(
        string='Status',
        selection=[('pending', 'Pending GRN'),
                   ('pending_verification', 'Pending Verification'),
                   ('recheck', 'Recheck GRN'),
                   ('recheck_completed', 'Recheck Completed'),
                   ('recheck_verification', 'Recheck Verification'),
                   ('completed', 'GRN Completed'),
                   ], tracking=True)
    grn_entered_by = fields.Many2one('res.users', 'GRN Entered By')
    grn_date = fields.Datetime('GRN Date')

    show_grn_status = fields.Boolean("Show GRN Status")
    is_any_variation_on_grn = fields.Boolean("Is any variation on grn")

    grn_status_pending_visibility = fields.Boolean("Show GRN Status Pending", compute='_get_grn_status_visibility')
    grn_status_completed_visibility = fields.Boolean("Show GRN Status Completed", compute='_get_grn_status_visibility')
    grn_status_completed_visibility_difference = fields.Boolean("Show GRN Status Completed Difference", compute='_get_grn_status_visibility')

    bl_entry_id = fields.Many2one('bl.entry', 'BL')
    bl_entry_container_id = fields.Many2one('bl.entry.container', 'Container')

    grn_documents = fields.Many2many('ir.attachment', string="GRN Document")

    is_grn_bin_allocation_created = fields.Boolean("Is grn bin allocation created?")

    is_stock_unloaded_in_outside_warehouse = fields.Boolean("Is stock unloaded in outside warehouse?",
                                                            compute='_get_stock_unloaded_in_outside')


    def update_after_discount_cost(self):
        # This method will update after discount cost of items in the lost and serial numbers

        for sa in self:
            for sa_line  in sa.shipment_summary_lines:
                for summ_line in sa_line.summary_lines:
                    print("\n\nsumm_line ==>> ", summ_line.lot_id)
                    lot_id = summ_line.lot_id

                    # Find Bl line containing discount information
                    bl_entry_container_id = sa.bl_entry_container_id

                    for bl_line in bl_entry_container_id.bl_entry_lines:
                        if bl_line.product_id.id == sa_line.product_id.id:

                            print("\n\nMatched BL Line   ==>> ", bl_line)
                            print("Product               ==>> ", sa_line.product_id.name)
                            fixed_discount_amount = bl_line.fixed_discount_amount
                            additional_discount = bl_line.additional_discount

                            print("fixed_discount_amount ==>> ", fixed_discount_amount)
                            print("additional_discount   ==>> ", additional_discount)

                            currency_id = bl_line.currency_id
                            product_packaging_id = bl_line.product_packaging_id

                            fixed_discount_amount = bl_line.fixed_discount_amount
                            additional_discount = bl_line.additional_discount

                            #Convert amount to aed
                            company_currency = self.env.company.currency_id
                            fixed_discount_amount = currency_id._convert(fixed_discount_amount, company_currency,
                                                                         self.env.company, fields.Date.today())
                            additional_discount = currency_id._convert(additional_discount, company_currency,
                                                                         self.env.company, fields.Date.today())




                            print("fixed_discount_amount AED ==>> ", fixed_discount_amount)
                            print("additional_discount   AED ==>> ", additional_discount)

                            print("product_packaging_id.qty  ==>> ", product_packaging_id.qty)
                            #Covert amount to base unit amount
                            if fixed_discount_amount > 0.0001:
                                fixed_discount_amount = fixed_discount_amount / product_packaging_id.qty
                            if additional_discount > 0.0001:
                                additional_discount = additional_discount / product_packaging_id.qty

                            print("fixed_discount_amount Base ==>> ", fixed_discount_amount)
                            print("additional_discount   Base ==>> ", additional_discount)

                            #Write values to lot and serial number

                            final_cost = lot_id.final_cost
                            final_cost_after_discount = final_cost - (fixed_discount_amount + additional_discount)
                            lot_id.write({
                                'fixed_discount' : fixed_discount_amount,
                                'additional_discount' : additional_discount,
                                'final_cost_after_discount' : final_cost_after_discount
                            })


    def _get_stock_unloaded_in_outside(self):
        # Find for this BL container is unloaded in our
        for shipment_advice in self:
            is_stock_unloaded_in_outside_warehouse = False
            if shipment_advice.bl_entry_id:
                is_stock_unloaded_in_outside_warehouse = shipment_advice.bl_entry_id.is_stock_unloaded_in_outside_warehouse
            shipment_advice.is_stock_unloaded_in_outside_warehouse = is_stock_unloaded_in_outside_warehouse



    def generate_landed_cost_from_bl(self):
        #This method to generate landed cost for item
        #
        #Total cost of BL is entered on BL entry itself
        #Based on the value of shipment advice, we find a percentage of cost will apply to shipment advice

        for advice in self:
            landed_cost_vals = {}

            #Finding the factor to apply, So we can get landed cost for this shipment advice
            bl_entry = advice.bl_entry_id

            #Value of item received
            shipment_advice_value = 0

            #For finding container value, we have to consider only the value of container as in bl
            container_id = advice.bl_entry_container_id
            shipment_advice_value = 0
            for bl_line in bl_entry.bl_entry_lines:
                if bl_line.container_id == container_id:
                    shipment_advice_value += bl_line.bl_total_price


            #Value of items in BL
            bl_value = 0
            for bl_line in bl_entry.bl_entry_lines:
                bl_value += bl_line.bl_total_price

            landed_cost_conversion_factor = shipment_advice_value/bl_value
            number_of_containers = len(bl_entry.bl_entry_container_ids)

            for bl_cost in bl_entry.bl_entry_costs:

                if bl_cost.type != 'actual':
                    raise UserError(_('On BL all costs should be actual'))

                if bl_cost.state == 'pending_approval':
                    raise UserError(_('Cost %s is not approved. Please get approval' % bl_cost.product_id.name))

                bl_cost.bl_entry_id.lock_cost_entry = True


                partner_id = bl_cost.partner_id.id

                if bl_cost.product_id.bl_to_container_split == 'by_value':
                    amount = bl_cost.amount * landed_cost_conversion_factor
                else:
                    amount = bl_cost.amount/number_of_containers

                taxes = bl_cost.tax_ids.compute_all(
                    amount,
                    currency=self.env.company.currency_id,
                    quantity=1.0
                )
                total_amount = taxes.get('total_included')

                landed_cost_res = {
                    'product_id' : bl_cost.product_id.id,
                    'description' : bl_cost.product_id.name,
                    'amount' : amount,
                    'tax_ids' : bl_cost.tax_ids and bl_cost.tax_ids.id or False,
                    'total_amount' : total_amount,
                    'split_method' : bl_cost.split_method,
                    'account_id' : bl_cost.account_id.id,
                    'bl_entry_cost' : bl_cost.id,
                    'date_added' : bl_cost.invoice_date,
                    'inv_no' : bl_cost.inv_no
                }

                if partner_id not in landed_cost_vals:
                    landed_cost_vals[partner_id] = {}
                    landed_cost_vals[partner_id][bl_cost.inv_no] = [(0, 0, landed_cost_res)]
                elif partner_id in landed_cost_vals:
                    if bl_cost.inv_no not in landed_cost_vals[partner_id]:
                        landed_cost_vals[partner_id][bl_cost.inv_no] = []
                        landed_cost_vals[partner_id][bl_cost.inv_no].append((0, 0, landed_cost_res))
                    else:
                        landed_cost_vals[partner_id][bl_cost.inv_no].append((0, 0, landed_cost_res))
                print('landed_cost_vals : ', landed_cost_vals)


            #Create Landed cost in shipment advice
            for partner_id in landed_cost_vals:
                for inv in landed_cost_vals[partner_id]:
                    landed_cost_res = {
                        'partner_id' : partner_id,
                        'shipment_advice_id' : advice.id,
                        'landed_cost_lines' : landed_cost_vals[partner_id][inv],
                        'date_added' : landed_cost_vals[partner_id][inv][0][2]['date_added'],
                        'inv_no': inv
                    }

                    landed_cost = self.env['shipment.advice.landed.cost'].create(landed_cost_res)

                    landed_cost.submit_landed_cost()


            #Load Custom Duty
            if bl_entry.bl_entry_costs_customs:

                if not bl_entry.customs_vendor_id:
                    raise UserError(_('Please select vendor for custom duty in BL'))

                if not bl_entry.customs_bill_date:
                    raise UserError(_('Please enter bill date in BL'))

                landed_cost_res = {
                    'partner_id': bl_entry.customs_vendor_id.id,
                    'shipment_advice_id': advice.id,
                    'date_added': bl_entry.customs_bill_date,
                    'inv_no': bl_entry.customs_inv_number
                }

                landed_cost = self.env['shipment.advice.landed.cost'].create(landed_cost_res)

                for cost in bl_entry.bl_entry_costs_customs:

                    if cost.container_id.id == advice.bl_entry_container_id.id:

                        cost.shipment_advice_id = advice.id
                        cost.sa_landed_cost_id = landed_cost.id

                landed_cost.submit_landed_cost()






    def _get_grn_status_visibility(self):

        for advice in self:
            grn_status_pending_visibility = False
            grn_status_completed_visibility = False
            grn_status_completed_visibility_difference = False

            if advice.show_grn_status:
                if advice.grn_entry_status == 'pending':
                    grn_status_pending_visibility = True
                elif advice.grn_entry_status == 'completed':
                    if advice.is_any_variation_on_grn:
                        grn_status_completed_visibility_difference = True
                    else:
                        grn_status_completed_visibility = True

            advice.grn_status_pending_visibility = grn_status_pending_visibility
            advice.grn_status_completed_visibility = grn_status_completed_visibility
            advice.grn_status_completed_visibility_difference = grn_status_completed_visibility_difference


    def send_documents_to_clearing_agent(self):

        self.ensure_one()
        ir_model_data = self.env['ir.model.data']

        template_id = ir_model_data._xmlid_lookup('kg_sarya_inventory.email_template_send_documents_to_clearing_agent')[2]

        try:
            compose_form_id = ir_model_data._xmlid_lookup('mail.email_compose_message_wizard_form')[2]
        except ValueError:
            compose_form_id = False

        attachment_ids = []
        for doc in self.attachment_ids:
            for attachment in doc.doc_attachment_partner:
                attachment_ids.append(attachment.id)

        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'shipment.advice',
            'active_model': 'shipment.advice',
            'active_id': self.ids[0],
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'custom_layout': "mail.mail_notification_paynow",
            'force_email': True,
            'model_description' : 'Send Document to Clearing Agent',
            'default_attachment_ids': attachment_ids,
            'mark_clearing_document_sent': True,
        })


        lang = self.env.context.get('lang')
        self = self.with_context(lang=lang)


        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        if self.env.context.get('mark_clearing_document_sent'):
            self.write({'is_docs_send_to_agent': True})
        return super(ShipmentAdvice, self.with_context(
            mail_post_autofollow=self.env.context.get('mail_post_autofollow', True))).message_post(**kwargs)


    def _compute_inspection_override(self):
        for advice in self:
            is_inspection_override_visible = False

            if advice.grn_entry_status == 'completed' and advice.state == 'item_in_receiving' and \
                    advice.inspection_method == 'inspection_at_warehouse':
                if advice.is_on_inspection:
                    for summary in advice.shipment_summary_lines:
                        if summary.balance_qty_in_inspection > 0.001:
                            is_inspection_override_visible = True

            if advice.inspection_method == 'inspection_at_warehouse' and advice.state == 'item_received':

                for summary in advice.shipment_summary_lines:
                    if summary.balance_qty_in_inspection > 0.001:
                        is_inspection_override_visible = True

            advice.is_inspection_override_visible = is_inspection_override_visible


    def inspection_confirm(self):
        self.is_inspected = True
        return {
            'name': _('Shipment Advise'),
            'res_model': 'shipment.advice',
            'type': 'ir.actions.act_window',
            'view_id': self.env.ref('kg_sarya_inventory.shipment_advice_form').id,
            'res_id': self.id,
            'view_mode': 'form',
            'view_type': 'form',
        }

    @api.onchange('bl_entry_container_id')
    def onchange_bl_entry_container_id(self):
        for shipment in self:
            shipment_lines = []
            bl_entry_container_id = shipment.bl_entry_container_id

            #Clear all existing lines
            shipment.shipment_lines = False

            matching_po = []
            for bl_line in bl_entry_container_id.bl_entry_lines:

                if bl_line.purchase_ids:
                    purchase_ids = bl_line.purchase_ids
                else:
                    purchase_ids = bl_line.bl_entry_id.purchase_ids

                #We need to find the po line, in order to create shipment advice line
                #Logic is to match product in po line with product in bl line
                matching_po_lines = []

                currency_id = False
                for purchase_id in purchase_ids:
                    currency_id = purchase_id.currency_id.id
                    for po_line in purchase_id.order_line:

                        #Matching po line
                        if po_line.product_id.id == bl_line.product_id.id:
                            matching_po_lines.append(po_line.id)
                            matching_po.append(purchase_id.id)


                lines_details = []
                for details in bl_line.qty_details:
                    lines_details.append((0, 0, {
                        'product_id' : bl_line.product_id.id,
                        'lpo_qty' : details.qty_to_receive,
                        'foc_qty' : details.foc_qty,
                        'qty_done' : details.qty_to_receive + details.foc_qty,
                        'expiry_date' : details.expiry_date,
                        'production_date' : details.production_date,
                        'bl_entry_line_details_id' : details.id
                    }))

                vals = {
                    'purchase_ids': [(6, 0, matching_po)],
                    'purchase_line_ids': [(6, 0, matching_po_lines)],
                    'product_id': bl_line.product_id.id,
                    'product_packaging_id': bl_line.product_packaging_id.id,
                    'pkg_unit_price': bl_line.bl_price,
                    'ci_qty': bl_line.bl_qty,
                    'currency_id': currency_id,
                    'shipment_line_details' : lines_details,
                    'bl_line' : bl_line.id
                }
                shipment_lines.append((0, 0, vals))
            shipment.update({ 'shipment_lines': shipment_lines,
                              'vendor_id' : shipment.bl_entry_id.vendor_id.id,
                              'purchase_ids' : [(6, 0, matching_po)],
                              'shipment_no' : shipment.bl_entry_id.shipment_no,
                              'boe_number': shipment.bl_entry_id.boe_number,
                              'zdlm': shipment.bl_entry_id.zdlm,
                              'departure_date' : shipment.bl_entry_id.departure_date,
                              'expected_date': shipment.bl_entry_id.expected_date,
                              })


    def inspection_completed_warehouse(self):
        for rec in self:
            rec.is_on_inspection = False

    def wh_inspection_completed(self):
        for rec in self:
            # 1.Do recive item to main stock
            rec.is_on_inspection = False
            rec.state = 'item_received'
            location_dest_id = self.main_stock_location.id
            location_id = self.inspection_location.id

            for landed_cost in rec.landed_cost_to_apply:
                if landed_cost.state != 'applied':
                    raise UserError(_('Please apply landed cost first'))


            self.create_picking_internal_transfer(location_id, location_dest_id,
                                                  transfer_desc='WH Inspection completed', mode='wh_inspection_main')


    def button_receive_stock_and_generate_bill_port(self):
        for rec in self:
            #1.Do recive item to main stock
            #self.verify_stock_entered()
            #rec._create_picking(mode='port_inspection')

            #2.Create bill
            #rec.bill_create_invoice()
            #rec.show_grn_status = False
            #rec.state = 'item_received'

            for summary_line in rec.shipment_summary_lines:
                for line in summary_line.summary_lines:
                    line.check_and_recompute_allocation()




            # 1. verify received and scrapped quantity is matching with shipped qty
            # self.verify_stock_entered()

            # 2.Do recive item to main stock
            rec._create_picking(mode='port_inspection')

            # 3.Create bill
            #rec.bill_create_invoice_per_po()

            # 4.Generate Debit Note
            #rec.debit_note_for_foc()

            # 5. Additional Discount Entry
            #rec.additional_discount_entry()



            # Status Update
            rec.show_grn_status = False
            rec.state = 'item_received'

            #6. Generating landed cost
            rec.generate_landed_cost_from_bl()




    def override_inspection_warehouse(self):
        for rec in self:

            for landed_cost in rec.landed_cost_to_apply:
                if landed_cost.state != 'applied':
                    raise UserError(_('Please apply landed cost first'))

            partial_receive = self.env['shipment.advice.receive.qty.partial'].create({'shipment_advice_id' : rec.id})

            for ship_summary in rec.shipment_summary_lines:
                for summary_line in ship_summary.summary_lines:

                    if summary_line.balance_qty_in_inspection > 0.001:
                        vals = {
                            'partial_id' : partial_receive.id,
                            'summary_line_id': summary_line.id,
                            'product_id' : summary_line.product_id.id,
                            'lot_id': summary_line.lot_id.id,
                            'expiry_date' : summary_line.expiry_date,
                            'production_date' : summary_line.production_date,
                            'qty_received_in_inspection' : summary_line.inspected_qty + summary_line.scrapped_qty,
                            'balance_qty_in_inspection' : summary_line.balance_qty_in_inspection,
                            'qty_for_mainstock' : summary_line.balance_qty_in_inspection,
                        }
                        self.env['shipment.advice.receive.qty.partial.line'].create(vals)

            return {
                'name': _('Inspection Override'),
                'res_model': 'shipment.advice.receive.qty.partial',
                'view_mode': 'form',
                'res_id': partial_receive.id,
                'target': 'new',
                'type': 'ir.actions.act_window',
                'views': [(self.env.ref("kg_sarya_inventory.view_shipment_advice_receive_qty_partial_form").id, "form")]
            }


            # 1.Do recive item to main stock
            location_dest_id = self.purchase_id.picking_type_id.default_location_dest_id.id
            location_id = self.inspection_location.id

            self.create_picking_internal_transfer(location_id, location_dest_id,
                                                  transfer_desc='WH Inspection Override', mode='wh_inspection_main')
            rec.state = 'item_received'

    def button_receive_stock_and_generate_bill_warehouse(self):
        for rec in self:

            for summary_line in rec.shipment_summary_lines:
                for line in summary_line.summary_lines:
                    line.check_and_recompute_allocation()




            for landed_cost in rec.landed_cost_to_apply:
                if landed_cost.state != 'applied':
                    raise UserError(_("Pending Landed Cost to Apply"))

            #1. verify received and scrapped quantity is matching with shipped qty
            #self.verify_stock_entered()

            #2.Do recive item to main stock
            rec._create_picking(mode='for_warehouse_inspection')

            #3.Create bill
            #rec.bill_create_invoice_per_po()

            #4.Generate Debit Note
            #rec.debit_note_for_foc()

            #5. Additional Discount Entry
            #rec.additional_discount_entry()


            #Status Update
            rec.show_grn_status = False
            rec.state = 'item_in_receiving'

            #6. Generating landed cost
            rec.generate_landed_cost_from_bl()


    def additional_discount_entry(self, bl):

        #Check there is any additional discount
        is_add_discount = False
        for advice in self:
            for shipment_line in advice.shipment_lines:
                additional_discount = shipment_line.bl_line.additional_discount
                if additional_discount > 0:
                    is_add_discount = True


        if not is_add_discount:
            return True

        purchase_order = True
        for po in self.purchase_ids:
            purchase_order = po


        move_line_vals = []


        debit_amount = 0
        for advice in self:
            for shipment_line in advice.shipment_lines:

                additional_discount = shipment_line.bl_line.additional_discount
                if additional_discount > 0:

                    #Find Foc Qty. We have to deduct foc qty form received qty
                    foc_qty = 0
                    for details in shipment_line.shipment_line_details:
                        foc_qty += details.foc_qty


                    total_received_qty = 0
                    all_summary = self.env['shipment.advice.summary'].search([('shipment_advice_id', '=', shipment_line.id)])
                    for summary in all_summary:
                        for summaly_line in summary.summary_lines:
                            total_received_qty = total_received_qty + summaly_line.inspected_qty

                    qty_for_addtitional_discount = total_received_qty - foc_qty

                    amount = qty_for_addtitional_discount * additional_discount

                    if amount > 0:

                        company_currency_id = self.env.company.currency_id
                        amount = purchase_order.currency_id._convert(
                            from_amount=amount, to_currency=company_currency_id,
                            company=self.env.company, date=datetime.utcnow().date())


                        name = "Additional Discount : %s %s %s" % (shipment_line.product_id.name, bl.name, advice.name)
                        debit_amount += amount

                        journal_entry = (0, 0, {
                            'account_id': advice.credit_acc_additional_disc.id,
                            'partner_id': purchase_order.partner_id.id,
                            'name': name,
                            'credit': amount,
                        })
                        move_line_vals.append(journal_entry)

        if move_line_vals:
            name = "Additional Discount : %s" % bl.name
            journal_entry = (0, 0, {
                'account_id': advice.debit_acc_additional_disc.id,
                'partner_id': purchase_order.partner_id.id,
                'name': name,
                'debit': debit_amount,
            })
            move_line_vals.append(journal_entry)


            move_obj = self.env['account.move'].with_context(default_move_type='entry')
            currency = purchase_order.currency_id

            create_entry = move_obj.create({'ref': 'Additional Discount : %s' % bl.name,
                                            'partner_id': purchase_order.partner_id.id,
                                            'invoice_date': date.today(),
                                            'line_ids': move_line_vals,
                                            'journal_id': advice.journal_additional_disc.id
                                            })
            create_entry.action_post()
            self.write({ 'additional_discounts' : [(4, create_entry.id)]})
            bl.write({'invoice_ids': [(4, create_entry.id)]})


    def bill_create_invoice_per_po(self):
        # Creating Bills for the items received

        po_ids = {}
        #Need to group shipment advices against po
        for advice in self:
            for purchase_order in advice.purchase_ids:

                # Check purchase is connected with any allocation
                allocation = self.env['lpo.wise.shipment.allocation'].search([
                    ('purchase_id', '=', purchase_order.id)])
                if not allocation:
                    self.message_post(body=_('Allocation missing for PO : %s') % purchase_order.name)
                    continue
                self.invoice_status = False

                if purchase_order.id not in po_ids:
                    po_ids[purchase_order.id] = [advice.id]

                elif advice.id not in po_ids[purchase_order.id]:
                    po_ids[purchase_order.id].append(advice.id)

        for purchase_id in po_ids:
            shipment_advices = self.env['shipment.advice'].browse(po_ids[purchase_id])
            purchase_order = self.env['purchase.order'].browse(purchase_id)
            is_last_po = True
            self.env['lpo.wise.shipment.allocation'].bill_create_invoice(purchase_order, shipment_advices, is_last_po)

    def bill_create_invoice_per_bl(self, bl):
        # Creating Bills for the items received

        po_ids = {}
        #Need to group shipment advices against po
        for advice in self:
            for purchase_order in advice.purchase_ids:

                # Check purchase is connected with any allocation
                allocation = self.env['lpo.wise.shipment.allocation'].search([
                    ('purchase_id', '=', purchase_order.id)])
                if not allocation:
                    self.message_post(body=_('Allocation missing for PO : %s') % purchase_order.name)
                    continue
                self.invoice_status = False

        self.env['lpo.wise.shipment.allocation'].bill_create_invoice_bl_wise(bl, self)



    def debit_note_for_foc_bl(self, bl):

        moves = self.env['account.move']

        #Check any FOC item received
        is_foc = False
        for advice in self:
            for shipment_line in advice.shipment_lines:
                for details in shipment_line.shipment_line_details:
                    if details.foc_qty > 0:
                        is_foc = True
        if not is_foc:
            return True

        purchase_order = True
        for advice in self:
            for po in advice.purchase_ids:
                purchase_order = po

        debit_note_vals = self._prepare_debit_note_for_foc(purchase_order, bl)
        debit_note_vals["invoice_origin"] = bl.name
        debit_note_vals["shipment_bill_number"] = bl.name

        # Creating Line for FOC
        debit_note_line_value = []
        for advice in self:
            for shipment_line in advice.shipment_lines:
                for details in shipment_line.shipment_line_details:
                    if details.foc_qty:
                        line_vals = advice._prepare_debit_note_line_for_foc(details)
                        debit_note_line_value.append((0, 0, line_vals))
        debit_note_vals['invoice_line_ids'] = debit_note_line_value

        foc = moves.create(debit_note_vals)
        foc.apply_po_discount()
        foc.action_post()
        self.write({'invoice_ids': [(4, foc.id)]})
        bl.write({'invoice_ids': [(4, foc.id)]})


    def _prepare_debit_note_line_for_foc(self, details):
        date = fields.Date.today()
        packaging_uom = details.shipment_advice_line_id.product_packaging_id.product_uom_id
        qty_per_packaging = details.shipment_advice_line_id.product_packaging_id.qty
        qty_to_invoice = details.foc_qty * qty_per_packaging
        price_unit = details.shipment_advice_line_id.pkg_unit_price / qty_per_packaging

        if not self.bl_entry_id.foc_credit_account_id:
            raise UserError(_('Please select FOC Credit Account'))


        res = {
            'name': 'FOC : %s %s' % (details.product_id.name, details.shipment_advice_line_id.shipment_id.name),
            #'product_id': details.product_id.id,
            'product_uom_id': details.product_id.uom_id.id,
            'quantity': qty_to_invoice,
            'price_unit': price_unit,
            'tax_ids': False,
            'purchase_line_id': False,
            'package_id': details.shipment_advice_line_id.product_packaging_id.id,
            'product_packaging_qty': details.foc_qty,
            'pkg_unit_price': details.shipment_advice_line_id.pkg_unit_price,
            'account_id' : self.bl_entry_id.foc_credit_account_id.id
        }
        return res


    def _prepare_debit_note_for_foc(self, purchase_order, bl):
        """Prepare the dict of values to create the new invoice for a purchase order.
        """
        move_type = 'in_refund'

        partner_invoice_id = purchase_order.partner_id.address_get(['invoice'])['invoice']

        ref = "FOC Received " + bl.name

        if bl.boe_number:
            ref = "%s %s" % (ref, bl.boe_number)

        invoice_vals = {
            'ref': ref,
            'move_type': move_type,
            'narration': bl.notes,
            'currency_id': purchase_order.currency_id.id,
            'invoice_user_id': self.user_id and self.user_id.id or self.env.user.id,
            'partner_id': partner_invoice_id,
            'payment_reference': ref,
            'partner_bank_id': purchase_order.partner_id.bank_ids[:1].id,
            'invoice_origin': bl.name,
            'invoice_payment_term_id': purchase_order.payment_term_id.id,
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
            'invoice_date': date.today(),
            'l10n_in_gst_treatment': bl.l10n_in_gst_treatment
        }
        return invoice_vals

    def verify_stock_entered(self):
        #Function to verify received and scrapped quantity is matching with shipped qty
        for rec in self:
            msg = ""
            for ship_sum_line in rec.shipment_summary_lines:
                ship_sum_line.qty_not_matching = False
                received_qty = ship_sum_line.inspected_qty
                if ship_sum_line.shipped_packaging_qty != received_qty:
                    ship_sum_line.qty_not_matching = True
                    msg = "%s \n %s" % (msg, ship_sum_line.product_id.name)
            if msg:
                msg = "Received qty is not matching shipped qty for following products\n" + msg
                raise ValidationError(msg)

    def apply_for_inspection(self):
        for rec in self:
            context = self.env.context.copy()
            vals = {
                'shipment_advice_id': self.id
            }
            shipment_advice = self.env['shipment.advice.inspection.date'].create(vals)
            view_id = self.env.ref('kg_sarya_inventory.shipment_advice_inspection_date_view').id
            return {
                'type': 'ir.actions.act_window',
                'name': _('Inspection Date'),
                'view_mode': 'form',
                'res_model': 'shipment.advice.inspection.date',
                'target': 'new',
                'res_id': shipment_advice.id,
                'views': [[view_id, 'form']],
                'context': context,
            }

    def apply_for_reinspection(self):
        for rec in self:
            context = self.env.context.copy()
            vals = {
                'shipment_advice_id': self.id
            }
            shipment_advice = self.env['shipment.advice.inspection.date'].create(vals)
            view_id = self.env.ref('kg_sarya_inventory.shipment_advice_inspection_date_view').id
            return {
                'type': 'ir.actions.act_window',
                'name': _('Reinspection Date'),
                'view_mode': 'form',
                'res_model': 'shipment.advice.inspection.date',
                'target': 'new',
                'res_id': shipment_advice.id,
                'views': [[view_id, 'form']],
                'context': context,
            }

    def scrap_items(self):
        for rec in self:
            location_dest_id = rec.scrap_location.id
            location_id = self.main_stock_location.id
            self.create_picking_internal_transfer(location_id, location_dest_id,
                                                  transfer_desc='Item Scrapping', mode='scrap_items')

            self.is_scrapping_completed = True


    def do_inspection_at_port(self):
        for rec in self:
            rec.inspection_method = 'inspection_at_port'
            rec.state='inspection'
            rec.grn_entry_status = 'pending'
            rec.show_grn_status = True
            rec.create_summary()

            #Send email notification
            email_to = self.env['shipment.advice.config'].get_email_for_3pl()
            if email_to:
                subject = "GRN pending for container : %s" % rec.bl_entry_container_id.container_number
                mail_content = "Please open Odoo portal and input GRN entry for container %s" % rec.bl_entry_container_id.container_number
                self.send_email_notifications(email_to, subject, mail_content)



    def do_inspection_at_warehouse(self):
        for rec in self:
            rec.inspection_method = 'inspection_at_warehouse'
            rec.state = 'inspection'
            rec.grn_entry_status = 'pending'
            rec.show_grn_status = True
            rec.create_summary()

            # Send email notification
            email_to = self.env['shipment.advice.config'].get_email_for_3pl()
            if email_to:
                subject = "GRN pending for container : %s" % rec.bl_entry_container_id.container_number
                mail_content = "Please open Odoo portal and input GRN entry for container %s" % rec.bl_entry_container_id.container_number
                self.send_email_notifications(email_to, subject, mail_content)



    def mark_grn_entry_approved(self):
        print("dddddddddddddddddddddddddd")
        #Sarya WH Team approve grn entry
        self.grn_entry_status = 'completed'

        # Send email notification
        email_to = self.env['shipment.advice.config'].get_email_for_grn_completed()
        if email_to:
            subject = "GRN entry is completed for container : %s" % self.bl_entry_container_id.container_number
            mail_content = "GRN entry is completed for container %s. \
                            Please complete entry of shipment advice" % self.bl_entry_container_id.container_number
            self.send_email_notifications(email_to, subject, mail_content)


    def send_grn_for_rechecking(self):
        print("dddddddddddddddddddddddddd")
        #Sarya WH Team send grn back to al sharqi for rechecking
        self.grn_entry_status = "recheck"

        # Send email notification
        email_to = self.env['shipment.advice.config'].get_email_for_3pl()
        if email_to:
            subject = "Recheck is required for container : %s" % self.bl_entry_container_id.container_number
            mail_content = "Please recheck GRN entry for container %s. \
                    Please contact Sarya Warehouse team for more details" % self.bl_entry_container_id.container_number
            self.send_email_notifications(email_to, subject, mail_content)



    def mark_grn_rechecking_completed(self):
        #Alsharqi Completes the rechecking and sending for approval
        self.compare_grn_entry_with_shipment_advice()
        self.grn_entry_status = 'recheck_completed'

        # Send email notification
        email_to = self.env['shipment.advice.config'].get_email_for_grn_verification()
        if email_to:
            subject = "GRN ReCheck is completed by 3PL. Please verify GRN entry for container : %s" % self.bl_entry_container_id.container_number
            mail_content = "Please open Odoo and check Recheck done by 3PL for container %s" % self.bl_entry_container_id.container_number
            self.send_email_notifications(email_to, subject, mail_content)



    def mark_grn_entry_completed(self):
        # Alsharqi Completes normal grn entry and sending for approval
        self.compare_grn_entry_with_shipment_advice()
        self.grn_entry_status = 'pending_verification'

        # Send email notification
        email_to = self.env['shipment.advice.config'].get_email_for_grn_verification()
        if email_to:
            subject = "GRN completed by 3PL. Please verify GRN entry for container : %s" % self.bl_entry_container_id.container_number
            mail_content = "Please open Odoo and check GRN entry for container %s" % self.bl_entry_container_id.container_number
            self.send_email_notifications(email_to, subject, mail_content)



    def approve_grn_rechecking(self):
        #Sending GRN to Jung for approval
        self.grn_entry_status = 'recheck_verification'

        # Send email notification
        email_to = self.env['shipment.advice.config'].get_email_for_recheck_verification()
        if email_to:
            subject = "Approval Required. For Container %s Rechecking is completed" % self.bl_entry_container_id.container_number
            mail_content = "Please open Odoo and approve rechecking done on GRN %s" % self.bl_entry_container_id.container_number
            self.send_email_notifications(email_to, subject, mail_content)


    def send_to_recheck_from_verification(self):
        # Jung send grn back to al-sharqi for recheck again
        self.grn_entry_status = 'recheck'

        # Send email notification
        email_to = self.env['shipment.advice.config'].get_email_for_3pl()
        if email_to:
            subject = "Recheck is requested by Purchase Manager for the container : %s" % self.bl_entry_container_id.container_number
            mail_content = "Please recheck GRN entry for container %s. \
                          Please contact Sarya Purchase Manager for more details" % self.bl_entry_container_id.container_number
            self.send_email_notifications(email_to, subject, mail_content)



    def do_recheck_verification(self):
        #Jung approves rechecked GRN
        self.grn_entry_status = 'completed'

        # Send email notification
        email_to = self.env['shipment.advice.config'].get_email_for_grn_completed()
        if email_to:
            subject = "GRN entry is completed for container : %s" % self.bl_entry_container_id.container_number
            mail_content = "GRN entry is completed for container %s. \
                                    Please complete entry of shipment advice" % self.bl_entry_container_id.container_number
            self.send_email_notifications(email_to, subject, mail_content)


    def send_email_notifications(self, email_to, subject, mail_content):
        main_content = {
            'subject': _(subject),
            'author_id': self.env.user.partner_id.id,
            'body_html': mail_content,
            'email_to': email_to,
        }
        self.env['mail.mail'].sudo().create(main_content).send()


    def compare_grn_entry_with_shipment_advice(self):
        for rec in self:
            is_any_variation_on_grn = False
            for summary_line in rec.shipment_summary_lines:
                for line in summary_line.summary_lines:
                    if line.qty_done != line.inspected_qty:
                        is_any_variation_on_grn = True
                        summary_line.is_any_variation_on_grn = True
                        summary_line.type_of_variation_on_grn = 'Quantity Not Matching'
                        line.type_of_variation_on_grn = 'Quantity Not Matching'

                    if line.expiry_date != line.expiry_date_actual:
                        is_any_variation_on_grn = True
                        summary_line.is_any_variation_on_grn = True
                        summary_line.type_of_variation_on_grn = 'Expiry Not Date Matching'
                        line.type_of_variation_on_grn = 'Expiry Not Date Matching'

                    if not line.expiry_date:
                        is_any_variation_on_grn = True
                        summary_line.is_any_variation_on_grn = True
                        summary_line.type_of_variation_on_grn = 'Different Expiry Received'
                        line.type_of_variation_on_grn = 'Different Expiry Received'
            rec.is_any_variation_on_grn = is_any_variation_on_grn


    def create_summary(self):
        summary_lines = []
        for sl in self.shipment_lines:
            summary_values = {
                'product_id': sl.product_id.id,
                'product_packaging_id': sl.product_packaging_id.id,
                'shipped_packaging_qty': sl.ci_qty,
                'scrapped_package_qty': 0.0,
                'shipment_advice_id' : sl.id,
#                'purchase_line_id' : sl.purchase_line_id.id,
                'purchase_ids' : [(6, 0, sl.purchase_ids.ids)],
                'purchase_line_ids' : [(6, 0, sl.purchase_line_ids.ids)]
            }

            summary_value_lines = []
            for sld in sl.shipment_line_details:

                lot_id = False
                #Commenting Lot create at the this stage
                #
                #

                # lot = self.env['stock.lot'].search(
                #     [('name', '=', sld.lot_name),
                #      ('company_id', '=', self.env.company.id),
                #      ('product_id', '=', sl.product_id.id)])
                # if lot:
                #     lot_id = lot.id
                # else:
                #     lot = self.env['stock.lot'].create({'name': sld.lot_name,
                #          'company_id': self.env.company.id,
                #          'expiration_date': sld.expiry_date,
                #          'product_id': sl.product_id.id})
                #     lot._compute_product_expiry_alert()
                #     lot_id = lot.id

                summary_value_line_value = {
                    'lot_name' : sld.lot_name,
                    'expiry_date' : sld.expiry_date,
                    'production_date' : sld.production_date,
                    'qty_done' : sld.qty_done,
                    'lot_id' : lot_id,
                    'shipment_advice_line_details' : sld.id
                }
                summary_value_lines.append((0, 0, summary_value_line_value))

            summary_values['summary_lines'] = summary_value_lines
            summary_lines.append((0, 0, summary_values))

        self.write({
            'shipment_summary_lines' : summary_lines,
            'shipment_summary_generated' : True
        })


    @api.depends('shipment_lines')
    def _compute_count(self):
        for rec in self:
            if rec.shipment_lines:
                pickings = rec.shipment_lines.mapped("purchase_id.picking_ids")
                purchase_ids = rec.shipment_lines.mapped("purchase_id")
                rec.picking_count = len(pickings)
                rec.purchase_count = len(purchase_ids)
                rec.invoice_count = len(rec.invoice_ids)
                rec.discount_count = len(rec.additional_discounts)
            else:
                rec.picking_count = 0
                rec.purchase_count = 0
                rec.invoice_count = 0
                rec.discount_count = 0


    def name_get(self):
        result = []
        for rec in self:
            if rec.bill_no:
                result.append((rec.id, '[%s] %s' % (rec.bill_no, rec.name)))
            else:
                result.append((rec.id, '[%s, %s] %s' % (rec.bl_entry_id.name, rec.bl_entry_container_id.container_number, rec.name)))
        return result

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('bill_no', operator, name)]
        return super(ShipmentAdvice, self)._name_search(name, domain=domain, operator=operator, limit=limit, order=order)

    @api.model
    def create(self, vals):
        if not vals.get('name') or vals['name'] == _('New'):
            vendor = self.env['res.partner'].search([('id', '=', vals.get('vendor_id'))]).name
            vendor_code = vendor[0:3]
            ir_record = self.env['shipment.advice'].search([], limit=1, order="id desc")
            seq = self.env['ir.sequence']
            year = str(date.today().year)
            l = len(year)
            yr = year[l - 2:]
            sequence = str(vendor_code) + "-" + str(yr) + "-SA00" + str(seq.next_by_code('shipment.advice'))
            vals['name'] = sequence or _('New')
            vals['next_id'] = seq
        res = super(ShipmentAdvice, self).create(vals)
        for po in self.purchase_ids:
            po.update_shipping_status()
        # fix attachment ownership
        for template in res:
            if template.grn_documents:
                template.grn_documents.sudo().write({'res_model': self._name, 'res_id': template.id})

        return res


    def write(self, vals):
        res = super(ShipmentAdvice, self).write(vals)
        #if 'purchase_ids' in vals:
        for po in self.purchase_ids:
            po.update_shipping_status()
        return res

    def unlink(self):
        po_list = []
        for po in self.purchase_ids:
            po_list.append(po)
        res = super(ShipmentAdvice, self).unlink()
        for po in po_list:
            po.update_shipping_status()
        return res


    @api.ondelete(at_uninstall=False)
    def _unlink_if_not_draft(self):
        for advise in self:
            if advise.state == 'done' or advise.state == 'open':
                raise UserError(_('You can only delete draft shipment advise.'))


    def action_view_invoice(self, invoices):
        result = self.env['ir.actions.act_window']._for_xml_id('account.action_move_in_invoice_type')
        # choose the view_mode accordingly
        if len(invoices) > 1:
            result['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            res = self.env.ref('account.view_move_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(state, view) for state, view in result['views'] if view != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = invoices.id
        else:
            result = {'type': 'ir.actions.act_window_close'}

        return result

    def action_cancel(self):
        for rec in self:
            if rec.state == 'cancel':
                pass
            # if rec.state not in ('draft', 'open'):
            #     raise UserError(_("You cannot cancel the shipment advice %s as it is already proceeded.") % rec.name)
            rec.shipment_lines.mapped('purchase_id.picking_ids').action_cancel()
            rec.shipment_lines.mapped('purchase_id.invoice_ids').button_cancel()
            rec.shipment_summary_lines.unlink()
            rec.shipment_lines.write({
                'received_packaging_qty': 0.0
            })
            rec.write({
                'state': 'cancel',
            })
            for entry in rec.entry_ids:
                entry.entry_ids.buttton_draft()
                entry.entry_ids.button_cancel()

    def action_reset(self):
        for rec in self:
            if rec.state == 'draft':
                pass
            rec.write({
                'state': 'draft',
            })

    def _create_picking(self, mode):
        # Creating picking. Mode can following values
        # 1.for_warehouse_inspection, items will be received to temporary location
        # 2.warehouse_inspection_release, item will be moved from temporary location to main stock
        # 3.port_inspection, items will be received directly to main stock

        StockPicking = self.env['stock.picking']
        for purchase_order in self.purchase_ids:

            #Check purchase is connected with any allocation
            allocation = self.env['lpo.wise.shipment.allocation'].search([
                ('purchase_id', '=', purchase_order.id)])
            if not allocation:
                continue

            #continue if stock allocation is against po
            picking_vals = purchase_order._prepare_picking()

            #If warehouse inspection items are received to temporary location with in the warehouse
            if mode == 'for_warehouse_inspection':
                picking_vals['location_dest_id'] = self.inspection_location.id
            else:
                picking_vals['location_dest_id'] = self.main_stock_location.id
            if mode == 'warehouse_inspection_release':
                picking_vals['location_id'] = self.inspection_location.id

            #Creating picking
            picking = StockPicking.with_user(SUPERUSER_ID).create(picking_vals)

            #Creating purchase order line from allocation
            moves = self.env['lpo.wise.shipment.allocation'].create_stock_moves(picking, mode, purchase_order, self)

            picking.shipment_id = self.id
            picking._message_log_with_view('mail.message_origin_link',
                                           render_values={'self': picking, 'origin': self})
            if picking:
                picking.action_confirm()
                picking.button_validate()
            purchase_order.update_receiving_status()

        return True


    def prepare_picking_val(self, purchase_order, mode):

        # continue if stock allocation is against po
        picking_vals = purchase_order._prepare_picking()

        # If warehouse inspection items are received to temporary location with in the warehouse
        if mode == 'for_warehouse_inspection':
            picking_vals['location_dest_id'] = self.inspection_location.id
        else:
            picking_vals['location_dest_id'] = self.main_stock_location.id
        if mode == 'warehouse_inspection_release':
            picking_vals['location_id'] = self.inspection_location.id

        return picking_vals



    def create_picking_internal_transfer(self, location_id, location_dest_id,
                                         transfer_desc='Stock Transfer', mode='wh_inspection_main'):
        self.ensure_one()

        picking_type_id = self.env['stock.picking.type'].search([('name', '=', 'Internal Transfers')], limit=1)
        if not picking_type_id:
            raise UserError(_("Internal Transfers operation type is not found in system"))

        # Create picking and move lines
        picking_vals = {
                'picking_type_id': picking_type_id.id,
                'user_id': False,
                'date': fields.Datetime.now(),
                'location_dest_id': location_dest_id,
                'location_id': location_id,
                'company_id': self.company_id.id,
                'immediate_transfer': True,
                'origin' : self.name + " : " + transfer_desc
            }

        picking = self.env['stock.picking'].create(picking_vals)

        for ship_sum_lines in self.shipment_summary_lines:
            if mode == 'wh_inspection_main':
                if ship_sum_lines.inspected_qty > 0 or ship_sum_lines.scrapped_package_qty > 0:
                    move_vals = ship_sum_lines.prepare_picking_line_int_trasnfer(picking, picking_type_id,
                                                location_id, location_dest_id,
                                                description=self.name + " : " + transfer_desc, mode=mode)
                    self.env['stock.move.line'].create(move_vals)

            elif mode == 'scrap_items':
                if ship_sum_lines.scrapped_package_qty > 0.001:
                    move_vals = ship_sum_lines.prepare_picking_line_int_trasnfer(picking, picking_type_id,
                                                location_id, location_dest_id,
                                                description=self.name + " : " + transfer_desc, mode=mode)
                    self.env['stock.move.line'].create(move_vals)

        picking.button_validate()
        picking.shipment_id = self.id


    def action_view_stock_moves(self):
        action = self.env.ref("stock.stock_move_action").sudo().read()[0]
        # remove default filters
        action["context"] = {}
        lines = self.shipment_lines.mapped("purchase_line_id.move_ids")
        if len(lines) > 1:
            action["domain"] = [("id", "in", lines.ids)]
        elif lines:
            action["views"] = [(self.env.ref("stock.view_move_form").id, "form")]
            action["res_id"] = lines.id
        return action

    def action_view_purchase(self):
        action = self.env.ref("purchase.purchase_form_action").sudo().read()[0]
        # remove default filters
        action["context"] = {}
        purchase_ids = self.shipment_lines.mapped("purchase_id")
        if len(purchase_ids) > 1:
            action["domain"] = [("id", "in", purchase_ids.ids)]
        elif purchase_ids:
            action["views"] = [(self.env.ref("purchase.purchase_order_form").id, "form")]
            action["res_id"] = purchase_ids.id
        return action

    def action_view_discount(self):
        action = self.env.ref("account.action_move_in_invoice_type").sudo().read()[0]
        # remove default filters
        action["context"] = {}
        invoice_ids = self.additional_discounts
        if len(invoice_ids) > 1:
            action["domain"] = [("id", "in", invoice_ids.ids)]
        elif invoice_ids:
            action["views"] = [(self.env.ref("account.view_move_form").id, "form")]
            action["res_id"] = invoice_ids.id
        return action


    def action_view_invoices(self):
        action = self.env.ref("account.action_move_in_invoice_type").sudo().read()[0]
        # remove default filters
        action["context"] = {}
        invoice_ids = self.invoice_ids
        if len(invoice_ids) > 1:
            action["domain"] = [("id", "in", invoice_ids.ids)]
        elif invoice_ids:
            action["views"] = [(self.env.ref("account.view_move_form").id, "form")]
            action["res_id"] = invoice_ids.id
        return action


    def action_view_pickings(self):
        action = self.env.ref("stock.action_picking_tree_all").sudo().read()[0]
        # remove default filters
        action["context"] = {}
        pickings = self.env['stock.picking'].search([('shipment_id', '=', self.id)])
        if len(pickings) > 1:
            action["domain"] = [("id", "in", pickings.ids)]
        elif pickings:
            action["views"] = [(self.env.ref("stock.view_picking_form").id, "form")]
            action["res_id"] = pickings.id
        else:
            return False
        return action


class ShipmentAdviceLine(models.Model):
    _name = 'shipment.advice.line'
    _description = 'Shipment Advice Line'
    _rec_name = 'product_id'

    shipment_id = fields.Many2one(
        'shipment.advice', 'Shipment', ondelete='cascade', required=True)

    purchase_id = fields.Many2one('purchase.order', 'Purchase', ondelete='cascade', copy=False,
                                  domain="[('state', 'in', ('purchase', 'done')), ('stock_type', '=', 'inventory')]")

    purchase_ids = fields.Many2many('purchase.order',
                                    'sarya_shipment_advice_line_purchase_order',
                                    "shipment_advice_line_id", "purchase_id",
                                    required=True)

    purchase_line_ids = fields.Many2many('purchase.order.line',
                                    'sarya_shipment_advice_line_purchase_order_line',
                                    "shipment_advice_line_id", "purchase_line_id")



    shipment_line_details = fields.One2many(comodel_name='shipment.advice.line.details', inverse_name='shipment_advice_line_id',
                                     string='Shipment Products', required=False, tracking=True)


    purchase_line_id = fields.Many2one(
        'purchase.order.line', 'Product Description',
        domain="[('order_id', '=', purchase_id)]")

    product_id = fields.Many2one('product.product', 'Product')

    company_id = fields.Many2one(related='shipment_id.company_id')

    product_packaging_id = fields.Many2one('product.packaging', string='Packaging')

    lpo_qty = fields.Float('LPO Qty')

    lpo_price = fields.Monetary('LPO Price')

    pi_qty = fields.Float(string="PI Qty")

    open_packaging_qty = fields.Float(string='Balance qty to receive on the LPO', readonly=1)
    ci_qty = fields.Float(string='CI Qty', compute='get_ci_qty',
                                         digits='Product Unit of Measure')

    shipped_packaging_qty = fields.Float(string='Shipped Qty (CI Qty)', compute='get_shipped_packaging_qty', digits='Product Unit of Measure')

    state = fields.Selection(string='Shipment Status', related='shipment_id.state')

    currency_id = fields.Many2one('res.currency')
    pkg_unit_price = fields.Monetary('CI Price')

    total_amount = fields.Monetary('CI Price x Qty', compute='compute_total')

    is_ci_not_matching = fields.Boolean("Commercial invoicing not matching?")

    fixed_discount_amount = fields.Monetary("Fixed Discount Amount", compute='get_fixed_discount_amount')

    price_after_fixed_discount = fields.Monetary("Price After Fixed Discount", compute='get_fixed_discount_amount')

    additional_discount = fields.Monetary("Additional Discount", compute='compute_total')

    bl_line = fields.Many2one('bl.entry.lines', 'BL Line')

    def write(self, vals):
        res = super(ShipmentAdviceLine, self).write(vals)
        self.re_gen_stock_allocation_lpo()
        return res

    def create(self, vals):
        res = super(ShipmentAdviceLine, self).create(vals)
        res.re_gen_stock_allocation_lpo()
        return res

    def re_gen_stock_allocation_lpo(self):

        for line in self:
            all_allocation = self.env['lpo.wise.shipment.allocation'].search([
                ('shipment_advice_line', '=', line.id)])
            if all_allocation:
                all_allocation.unlink()
            #self.alert_is_over_stock_receiving(line)

            for details in line.shipment_line_details:
                details.allocate_stock_against_lpo(details.qty_done, details.shipment_advice_line_id.shipment_id.id,
                                                details.shipment_advice_line_id.id, details.id)

    def alert_is_over_stock_receiving(self, shipment_advice_line):

        #Only FOC can be received more than the PO Qty.
        #Non FOC quantity cannot be received more than the PO Qty

        #Find total qty in purchase line to receive
        total_pending_qty_to_ship = 0
        for po_line in shipment_advice_line.purchase_line_ids.sorted('id'):

            po_allocation = self.env['lpo.wise.shipment.allocation'].search([
                ('purchase_line_id', '=', po_line.id)])
            po_allocation_qty = 0
            for alloc in po_allocation:
                po_allocation_qty += alloc.shipment_advice_line_qty

            pending_qty_to_ship = po_line.product_packaging_qty - po_allocation_qty
            total_pending_qty_to_ship += pending_qty_to_ship

        #Find total LPO qty entered by user
        total_lpo_qty = 0
        for details in shipment_advice_line.shipment_line_details:
            total_lpo_qty += details.lpo_qty

        #compare
        if total_pending_qty_to_ship < total_lpo_qty:
            raise UserError(_("You cannot receive more qty than in LPO, Pending qty to receive in LPO is %s %s" %
                              (str(total_pending_qty_to_ship), shipment_advice_line.product_id.name)))


    def get_fixed_discount_amount(self):

        for advice in self:
            fixed_discount_amount = 0
            price_after_fixed_discount = 0
            suppiler_info = self.env['product.supplierinfo'].search([('partner_id', '=', advice.shipment_id.vendor_id.id),
                                                    ('product_tmpl_id', '=', advice.product_id.product_tmpl_id.id)])

            if suppiler_info:
                disc1 = suppiler_info.discount_1
                disc2 = suppiler_info.discount_2
                total_discount = disc1 + disc2
                fixed_discount_amount = advice.lpo_price * total_discount

            advice.fixed_discount_amount = fixed_discount_amount

            advice.price_after_fixed_discount = advice.lpo_price - fixed_discount_amount




    @api.depends('shipment_line_details.qty_done', 'pkg_unit_price')
    def compute_total(self):
        for rec in self:
            shipped_packaging_qty = 0
            additional_discount = 0
            for details in rec.shipment_line_details:
                shipped_packaging_qty = shipped_packaging_qty + details.lpo_qty
            rec.total_amount = shipped_packaging_qty * rec.pkg_unit_price
            rec.additional_discount = rec.price_after_fixed_discount - rec.pkg_unit_price


    @api.depends('shipment_line_details.qty_done')
    def get_ci_qty(self):
        for rec in self:
            ci_qty = 0
            for details in rec.shipment_line_details:
                ci_qty = ci_qty + details.qty_done
            rec.ci_qty = ci_qty

    @api.depends('shipment_line_details.qty_done')
    def get_shipped_packaging_qty(self):
        for rec in self:
            shipped_packaging_qty = 0
            for details in rec.shipment_line_details:
                shipped_packaging_qty = shipped_packaging_qty + details.qty_done
            rec.shipped_packaging_qty = shipped_packaging_qty


    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            po_lines = self.env['purchase.order.line'].search(
                [('order_id.state', 'in', ('purchase', 'done')), ('order_id.is_closed', '=', False),
                 ('order_id.stock_type', '=', 'inventory'),
                 ('product_id', '=', self.product_id.id)])
            po_line_ids = po_lines.filtered(lambda l: (l.product_uom_qty - l.shipment_adv_qty) > 0)
            return {
                'domain': {
                    'purchase_id': [('id', 'in', po_line_ids.mapped('order_id').ids)]
                }
            }

    @api.onchange('purchase_line_id')
    def _onchange_purchase_line_id(self):
        open_packaging_qty = 0.0
        received_qty_packaged = 0.0
        if self.purchase_line_id:
            packaging_uom = self.product_packaging_id.product_uom_id
            open_qty = self.purchase_line_id.product_uom_qty - self.purchase_line_id.shipment_adv_qty
            packaging_uom_qty = self.purchase_line_id.product_uom._compute_quantity(open_qty, packaging_uom)
            open_packaging_qty = float_round(packaging_uom_qty / self.product_packaging_id.qty,
                                             precision_rounding=packaging_uom.rounding)

            received_qty = self.purchase_line_id.qty_received
            received_qty_converted = self.purchase_line_id.product_uom._compute_quantity(received_qty, packaging_uom)
            received_qty_packaged = float_round(received_qty_converted / self.product_packaging_id.qty,
                                                precision_rounding=packaging_uom.rounding)
        self.update({
            'open_packaging_qty': open_packaging_qty,
            'shipped_packaging_qty': 0,
            'received_packaging_qty': 0,
        })

    @api.onchange('shipped_packaging_qty')
    def _onchange_shipped_packaging_qty(self):
        result = {}
        if self.shipped_packaging_qty > self.open_packaging_qty:
            result['warning'] = {
                'title': _('Warning'),
                'message': _('Shipped quantity should not be exceed open qty.'),
            }
        return result


class ShipmentAdviceLineDetails(models.Model):
    _name = 'shipment.advice.line.details'

    shipment_advice_line_id = fields.Many2one('shipment.advice.line', string='Shipment Advice Line', ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', string='Product', related="shipment_advice_line_id.product_id")
    lot_name = fields.Char("Lot Name")
    lot_id = fields.Many2one('stock.lot', string="Lot")
    expiry_date = fields.Date("Expiry Date")
    production_date = fields.Date(compute='_get_expiration_date', string="Production Date")
    qty_done = fields.Float("Qty Done")
    lpo_qty = fields.Float("LPO Qty")
    foc_qty = fields.Float("FOC Qty")

    bl_entry_line_details_id = fields.Many2one('bl.entry.lines.details', string='Bl Entry Details')

    @api.onchange('lpo_qty', 'foc_qty')
    def _onchange_lpo_qty_foc_qty(self):
        for detail in self:
            detail.qty_done = detail.lpo_qty + detail.foc_qty


    @api.depends('expiry_date', 'product_id')
    def _get_expiration_date(self):
        for rec in self:
            rec.production_date = False
            if rec.expiry_date and rec.product_id.shelf_life:
                rec.production_date = rec.expiry_date - timedelta(days=rec.product_id.shelf_life)
            else:
                if not rec.product_id.shelf_life and rec.expiry_date:
                    rec.production_date = rec.expiry_date - timedelta(days=365)

    #Cha commented to avoid auto generation of lot number during Commercial Invoice entry
    @api.onchange('product_id')
    def _onchange_product_id(self):
        times = str(round(time.time() * 1000))[-2:]
        sq_start = ""
        line_id = str(self.id)
        last_section = line_id[-4:]
        if len(self.product_id.default_code) > 5:
            sq_start = self.product_id.default_code[0:5] + times
        sq_start += last_section.upper()
        self.lot_name = sq_start


    def allocate_stock_against_lpo(self, qty_to_allocate, shipment_id,
                                   shipment_advice_line_id, shipment_advice_line_details_id):

        qty_allocated = 0
        #run until all qtys are allocated
        shipment_advice_line = self.env['shipment.advice.line'].browse(shipment_advice_line_id)

        while qty_to_allocate > 0:

            #Check line is already allocated

            is_purchase_line_qty_reached_max = True

            allocation = False
            for po_line in shipment_advice_line.purchase_line_ids.sorted('id'):

                po_allocation = self.env['lpo.wise.shipment.allocation'].search([
                    ('purchase_line_id', '=', po_line.id)])

                po_allocation_qty = 0
                for alloc in po_allocation:
                    po_allocation_qty += alloc.shipment_advice_line_qty

                pending_qty_to_ship = po_line.product_packaging_qty - po_allocation_qty

                if pending_qty_to_ship > 0:
                    is_purchase_line_qty_reached_max = False

                if pending_qty_to_ship > 0:

                    allocation = self.env['lpo.wise.shipment.allocation'].search([
                                ('shipment_advice_line_details', '=', shipment_advice_line_details_id),
                                ('purchase_line_id', '=', po_line.id)])

                    if not allocation:

                        allocation_vals = {'shipment_advice_id' : shipment_id,
                                           'shipment_advice_line' : shipment_advice_line_id,
                                           'shipment_advice_line_details' : shipment_advice_line_details_id,

                                           'purchase_id': po_line.order_id.id,
                                           'purchase_line_id': po_line.id,
                                           }

                        allocation = self.env['lpo.wise.shipment.allocation'].create(allocation_vals)

                    shipment_advice_line_qty = qty_to_allocate
                    if pending_qty_to_ship < shipment_advice_line_qty:
                        shipment_advice_line_qty = pending_qty_to_ship

                    qty_to_allocate = qty_to_allocate - shipment_advice_line_qty
                    allocation.shipment_advice_line_qty = shipment_advice_line_qty

                if qty_to_allocate == 0 or qty_to_allocate < 0:
                    break

            if qty_to_allocate == 0:
                break

            if is_purchase_line_qty_reached_max:

                if allocation:
                    allocation.shipment_advice_line_qty = allocation.shipment_advice_line_qty + qty_to_allocate
                    break
                else:
                    allocation_vals = {'shipment_advice_id': shipment_id,
                                       'shipment_advice_line': shipment_advice_line_id,
                                       'shipment_advice_line_details': shipment_advice_line_details_id,
                                       'shipment_advice_line_qty' : qty_to_allocate,

                                       'purchase_id': po_line.order_id.id,
                                       'purchase_line_id': po_line.id,
                                       }

                    allocation = self.env['lpo.wise.shipment.allocation'].create(allocation_vals)
                    break
                    #raise UserError(_('1567 Allocation cannot find'))

                raise UserError(_('You cannot receive more than on LPO Qty'))


class ShipmentAdviceTotal(models.Model):
    _name = 'shipment.advice.summary'
    _description = 'Shipment Advice Total'
    _rec_name = 'product_id'

    shipment_id = fields.Many2one(
        'shipment.advice', 'Shipment', ondelete='cascade', required=True)

    inspection_method = fields.Selection(string='Inspection method',
                                         selection=[('inspection_at_port', 'Inspection at port'),
                                                    ('inspection_at_warehouse', 'Inspection at warehouse')],
                                         related='shipment_id.inspection_method')

    shipment_advice_id = fields.Many2one('shipment.advice.line', string='Shipment Lines')
    product_id = fields.Many2one('product.product',
                                 string='Product',
                                 domain=[('purchase_ok', '=', True)],
                                 change_default=True)
    product_packaging_id = fields.Many2one('product.packaging',
                                           string='Packaging',
                                           domain="[('purchase', '=', True), ('product_id', '=', product_id)]",
                                           check_company=True)
    shipped_packaging_qty = fields.Float(string='Shipped Qty',
                                         digits='Product Unit of Measure')
    inspected_qty = fields.Float(string='Received Qty',
                                          digits='Product Unit of Measure')
    scrapped_package_qty = fields.Float(string='Scrapped Qty',
                                        digits='Product Unit of Measure')
    inspected_qty = fields.Float(string='Inspected Qty')
    reason = fields.Char()
    purchase_line_id = fields.Many2one(
        'purchase.order.line', 'Product Description')

    purchase_ids = fields.Many2many('purchase.order',
                                    'sarya_shipment_advice_summary_purchase_order',
                                    "shipment_summary_id", "purchase_id",
                                    required=True)

    purchase_line_ids = fields.Many2many('purchase.order.line',
                                         'sarya_shipment_advice_summary_purchase_order_line',
                                         "shipment_summary_line_id", "purchase_line_id")


    qty_not_matching = fields.Boolean("Qty not matching")


    summary_lines = fields.One2many('shipment.summary.line', 'summary_id')
    state = fields.Selection(
        string='Status',
        selection=[
            ('draft', 'Draft'),
            ('open', 'Open'),
            ('done', 'Closed'),
            ('cancel', 'Cancelled'),
        ],
        related='shipment_id.state')
    inspection_status = fields.Selection(
        [('not_inspected', 'Not Inspected'), ('inspecting', 'Inspecting'), ('inspected', 'Inspected')],
        related='shipment_id.inspection_status')
    inspected_qty = fields.Float(compute='get_line_ins_qty')

    scrapped_package_qty = fields.Float(string='Scrapped Qty', digits='Product Unit of Measure',
                                        compute='get_scrapped_package_qty')

    qty_moved_to_main_stock = fields.Float("Qty moved to Main Stock", store=False, compute='get_qty_moved_to_main_stock')
    balance_qty_in_inspection = fields.Float("Balance Qty in Inspection", store=False, compute='get_balance_qty_in_inspection')
    balance_qty_in_inspection_new = fields.Float("Balance Qty in Inspection", compute='get_balance_qty_in_inspection_new')
    qty_allocated_to_po = fields.Float("Qty Allocated to PO")
    is_any_variation_on_grn = fields.Boolean("Is any variation on grn")

    type_of_variation_on_grn = fields.Char("Variation")

    image = fields.Many2many('ir.attachment', string="Image")

    is_stock_unloaded_in_outside_warehouse = fields.Boolean("Is stock unloaded in outside warehouse?",
                                                            compute='_get_stock_unloaded_in_outside')

    def _get_stock_unloaded_in_outside(self):
        # Find for this BL container is unloaded in our
        for summary in self:
            is_stock_unloaded_in_outside_warehouse = False
            if summary.shipment_id and summary.shipment_id.bl_entry_id:
                is_stock_unloaded_in_outside_warehouse = summary.shipment_id.bl_entry_id.is_stock_unloaded_in_outside_warehouse
            summary.is_stock_unloaded_in_outside_warehouse = is_stock_unloaded_in_outside_warehouse



    @api.depends('summary_lines.qty_moved_to_main_stock')
    def get_balance_qty_in_inspection_new(self):
        for summary in self:
            balance_qty_in_inspection_new = 0
            for line in summary.summary_lines:
                balance_qty_in_inspection_new += line.balance_qty_in_inspection
            summary.balance_qty_in_inspection_new = balance_qty_in_inspection_new

    @api.depends('summary_lines.qty_moved_to_main_stock')
    def get_qty_moved_to_main_stock(self):
        for summary in self:
            qty_moved_to_main_stock = 0
            for line in summary.summary_lines:
                qty_moved_to_main_stock += line.qty_moved_to_main_stock
            summary.qty_moved_to_main_stock = qty_moved_to_main_stock

    @api.depends('summary_lines.qty_moved_to_main_stock')
    def get_balance_qty_in_inspection(self):
        for summary in self:
            balance_qty_in_inspection = 0
            for line in summary.summary_lines:
                balance_qty_in_inspection += line.balance_qty_in_inspection
            summary.balance_qty_in_inspection = balance_qty_in_inspection

    @api.depends('summary_lines.scrapped_qty')
    def get_scrapped_package_qty(self):
        for rec in self:
            scrapped_qty = 0.0
            for summ_line in rec.summary_lines:
                scrapped_qty = scrapped_qty + summ_line.scrapped_qty
            rec.scrapped_package_qty = scrapped_qty

    @api.depends('summary_lines.inspected_qty', 'summary_lines.scrapped_qty')
    def get_line_ins_qty(self):
        for rec in self:
            inspected_qty = 0.0
            for line in rec.summary_lines:
                inspected_qty += line.inspected_qty
            rec.inspected_qty = inspected_qty


    def prepare_picking_line_int_trasnfer(self, picking, picking_type_id,
                                      location_id, location_dest_id, description='', mode="wh_inspection_main"):
        self.ensure_one()
        vals = []
        for summary_line in self.summary_lines:
            # Finding qty against each lot received for same product
            if mode == 'wh_inspection_main':
                total_qty_received = summary_line.inspected_qty
                summary_line.qty_moved_to_main_stock = summary_line.qty_moved_to_main_stock + total_qty_received
            elif mode == 'scrap_items':
                total_qty_received = summary_line.scrapped_qty

            if total_qty_received > 0.001:
                packaging_uom = self.product_packaging_id.product_uom_id
                qty_per_packaging = self.product_packaging_id.qty

                # Convenrty packaging qty to uom qty
                total_qty_received = packaging_uom._compute_quantity(total_qty_received * qty_per_packaging, self.product_id.uom_id)
                product_uom_qty, product_uom = self.product_id.uom_id._adjust_uom_quantities(total_qty_received, self.product_id.uom_id)

                vals.append({
                    'product_id': self.product_id.id,
                    'date': fields.Datetime.now(),
                    'location_id': location_id,
                    'location_dest_id': location_dest_id,
                    'picking_id': picking.id,
                    'lot_id': summary_line.lot_id.id,
                    'company_id': self.purchase_line_id.order_id.company_id.id,
                    'origin': description,
                    'qty_done': product_uom_qty,
                    'product_uom_id': product_uom.id,
                    'product_packaging_id': self.product_packaging_id.id,
                })
        return vals


class ShipmentAdvSummeryLine(models.Model):
    _name = 'shipment.summary.line'

    summary_id = fields.Many2one(
		'shipment.advice.summary', 'Summery', ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product',related="summary_id.product_id")
    lot_name = fields.Char("Lot Name")
    lot_id = fields.Many2one('stock.lot')
    expiry_date = fields.Date("Expiry Date")

    expiry_date_actual = fields.Date("Expiry Date Actual")

    production_date_actual = fields.Date("Production Date Actual")

    production_date = fields.Date(compute='_get_expiration_date')
    qty_done = fields.Float("Qty Done", digits=(16, 3))
    inspected_qty = fields.Float("Inspected Qty", digits=(16, 3))

    received_qty_actual = fields.Float("Received Qty Actual", digits=(16, 6))

    scrapped_qty = fields.Float(string="Damaged Qty", digits=(16, 6))

    qty_short = fields.Float("Qty Short", digits=(16, 3))
    qty_excess = fields.Float("Qty Excess", digits=(16, 3))

    municipality_inspection_qty = fields.Float("Municipality Inspection Qty", digits=(16, 6))

    qty_moved_to_main_stock = fields.Float("Qty moved to Main Stock")
    balance_qty_in_inspection = fields.Float("Balance Qty in Inspection", compute='_get_balance_qty_in_inspection')

    qty_allocated_to_po = fields.Float("Qty Allocated to PO")
    shipment_advice_line_details = fields.Many2one('shipment.advice.line.details', string='Line Details')

    is_any_variation_on_grn = fields.Boolean("Is any variation on GRN")
    type_of_variation_on_grn = fields.Char("Variation")

    image = fields.Many2many('ir.attachment', string="Image")

    @api.onchange('inspected_qty', 'municipality_inspection_qty')
    def onchange_inspected_qty(self):

        for line in self:
            qty_short = line.qty_done - line.inspected_qty
            received_qty_actual = line.inspected_qty
            if qty_short > 0:
                line.qty_short = qty_short
            else:
                line.qty_short = 0

            qty_excess = line.inspected_qty - line.qty_done
            if qty_excess > 0:
                line.qty_excess = qty_excess
            else:
                line.qty_excess = 0

            if line.municipality_inspection_qty > 0:
                received_qty_actual = received_qty_actual - line.municipality_inspection_qty
            line.received_qty_actual = received_qty_actual



    # @api.onchange('expiry_date_actual')
    # def onchange_expiry_date_actual(self):
    #     #computing production date while Al Sharqi doing item receiving
    #     for rec in self:
    #         rec.production_date_actual = False
    #         if rec.expiry_date_actual and rec.product_id.shelf_life:
    #             rec.production_date_actual = rec.expiry_date_actual - timedelta(days=rec.product_id.shelf_life)
    #         else:
    #             if not rec.product_id.shelf_life and rec.expiry_date_actual:
    #                 rec.production_date_actual = rec.expiry_date_actual - timedelta(days=365)


    def create(self, vals):
        res = super(ShipmentAdvSummeryLine, self).create(vals)
        for ssl in res:
            if ssl.shipment_advice_line_details:
                allocation = self.env['lpo.wise.shipment.allocation'].search([
                    ('shipment_advice_line_details', '=', ssl.shipment_advice_line_details.id)])
                for alloc in allocation:
                    alloc.shipment_advice_summary_line = ssl.id
                    alloc.shipment_advice_summary = ssl.summary_id.id
            else:

                ssl.check_and_recompute_allocation()


        for template in res:
            if template.image:
                template.image.sudo().write({'res_model': self._name, 'res_id': template.id})

        return res

    def write(self, vals):
        res = super(ShipmentAdvSummeryLine, self).write(vals)
        self.allocate_qty_to_ship_allocation()
        return res

    def check_and_recompute_allocation(self):

        for line in self:
            allocation = self.env['lpo.wise.shipment.allocation'].search([
                ('shipment_advice_summary_line', '=', line.id)], order='purchase_id desc')

            if allocation:

                qty_to_allocated = 0
                for alloc in allocation:
                    qty_to_allocated += alloc.shipment_advice_summary_line_qty
                balance_qty_to_allocate = line.inspected_qty - qty_to_allocated

                if balance_qty_to_allocate > 0 and allocation:

                    for alloc in allocation:
                        if alloc.purchase_line_id.pending_qty_to_ship > 0:

                            extra_qty_allocate = balance_qty_to_allocate
                            if extra_qty_allocate > alloc.purchase_line_id.pending_qty_to_ship:
                                extra_qty_allocate = alloc.purchase_line_id.pending_qty_to_ship

                            alloc.shipment_advice_line_qty = alloc.shipment_advice_line_qty + extra_qty_allocate
                            alloc.shipment_advice_summary_line_qty = alloc.shipment_advice_summary_line_qty + extra_qty_allocate
                            balance_qty_to_allocate = balance_qty_to_allocate - extra_qty_allocate


                    if balance_qty_to_allocate > 0:
                        last_allocation = alloc
                        last_allocation.shipment_advice_summary_line_qty = last_allocation.shipment_advice_summary_line_qty + balance_qty_to_allocate

            else:
                purchase_id = False
                purchase_line_id = False
                for po_line in line.summary_id.purchase_line_ids.sorted('id', reverse=True):
                    purchase_id = po_line.order_id.id
                    purchase_line_id = po_line.id
                allocation_vals = {
                                   'shipment_advice_id': line.summary_id.shipment_id.id,
                                   'shipment_advice_summary' : line.summary_id.id,
                                   'shipment_advice_summary_line' : line.id,
                                   'purchase_id': purchase_id,
                                   'purchase_line_id': purchase_line_id,
                                   'shipment_advice_summary_line_qty' : line.inspected_qty
                                   }
                allocation = self.env['lpo.wise.shipment.allocation'].create(allocation_vals)

    def allocate_qty_to_ship_allocation(self):

        for line in self:
            allocation = self.env['lpo.wise.shipment.allocation'].search([
                ('shipment_advice_summary_line', '=', line.id)], order='purchase_id desc')

            #Clearing qty in allocation
            for alloc in allocation:
                #TEST
                alloc.shipment_advice_summary_line_qty = 0

            qty_to_allocate = line.inspected_qty

            for alloc in allocation:
                qty_allocated = qty_to_allocate
                if alloc.shipment_advice_line and alloc.shipment_advice_line_qty < qty_allocated and False:
                    qty_allocated = alloc.shipment_advice_line_qty
                alloc.shipment_advice_summary_line_qty = qty_allocated
                qty_to_allocate = qty_to_allocate - qty_allocated


    def _get_balance_qty_in_inspection(self):
        for line in self:
            balance_qty_in_inspection = (line.inspected_qty + line.scrapped_qty) - line.qty_moved_to_main_stock
            if line.summary_id.inspection_method != 'inspection_at_warehouse':
                balance_qty_in_inspection = 0
            line.balance_qty_in_inspection = balance_qty_in_inspection


    @api.depends('expiry_date','product_id')
    def _get_expiration_date(self):
        for rec in self:
            rec.production_date = False
            if rec.expiry_date and rec.product_id.shelf_life:
                rec.production_date = rec.expiry_date - timedelta(days=rec.product_id.shelf_life)
            else:
                if not rec.product_id.shelf_life and rec.expiry_date:
                    rec.production_date = rec.expiry_date - timedelta(days=365)



class StockPickingInh(models.Model):
    _inherit = 'stock.picking'
    shipment_id = fields.Many2one('shipment.advice')


class AccountJournalInherit(models.Model):
    _inherit = 'account.move'

    shipment_id = fields.Many2one('shipment.advice', string="Related Shipment", copy=False)


    def button_create_landed_costs(self):
        """Create a `stock.landed.cost` record associated to the account move of `self`, each
        `stock.landed.costs` lines mirroring the current `account.move.line` of self.
        """
        self.ensure_one()
        landed_costs_lines = self.line_ids.filtered(lambda line: line.is_landed_costs_line)

        landed_costs = self.env['stock.landed.cost'].create({
            'vendor_bill_id': self.id,
            'shipment_ids' : self.shipment_id.ids,
            'cost_lines': [(0, 0, {
                'product_id': l.product_id.id,
                'name': l.product_id.name,
                'account_id': l.shipment_advice_landed_cost_line_id and \
                              l.shipment_advice_landed_cost_line_id.account_id.id or \
                              l.bl_entry_custom_cost.account_id.id,
                'price_unit': l.currency_id._convert(l.price_subtotal, l.company_currency_id, l.company_id, l.move_id.date),
                'split_method': l.shipment_advice_landed_cost_line_id and \
                                l.shipment_advice_landed_cost_line_id.split_method or 'equal',
                'bl_custom_id': l.bl_entry_custom_cost and l.bl_entry_custom_cost.id or False
            }) for l in landed_costs_lines],
        })
        landed_costs.onchange_shipment_id()

        landed_costs.compute_landed_cost()
        landed_costs.button_validate()

        action = self.env["ir.actions.actions"]._for_xml_id("stock_landed_costs.action_stock_landed_cost")
        return dict(action, view_mode='form', res_id=landed_costs.id, views=[(False, 'form')])
