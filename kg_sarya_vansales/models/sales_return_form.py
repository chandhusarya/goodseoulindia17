# Copyright 2017-2020 ForgeFlow, S.L.

from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError, MissingError, UserError
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round, get_lang


class SalesReturnForm(models.Model):
    _name = "sales.return.form"
    _description = "Sales Return Form"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char('Reference #', copy=False, readonly=True)
    state = fields.Selection(
        selection=[("draft", "Draft"),
                   ("request", "Requested"),
                   ("approve", "Approved"),
                   ("reject", "Rejected"),
                   ("cancel", "Cancelled"), ],
        string="Status",
        copy=False,
        default="draft",
        index=True,
        readonly=True,
        tracking=True,
    )
    user_id = fields.Many2one("res.users", "Requested by", required=True, tracking=True,
                              default=lambda self: self.env.user.id)
    approve_user_id = fields.Many2one("res.users", "Approved by", copy=False, tracking=True)
    stock_user_id = fields.Many2one("res.users", "Store In-charge", copy=False, tracking=True)
    date = fields.Datetime("Return Date", default=fields.Datetime.now, index=True, required=True,
                           help="Date to receive the goods back.", )
    credit_note_date = fields.Date("Posting Date", index=True, required=True,
                                   help="Date to creating credit note.", )

    refund_date = fields.Datetime("Refund Date", default=fields.Datetime.now, index=True, required=True,
                                  help="Date of account entry.")
    type = fields.Selection(
        string='Return Type',
        selection=[('normal', 'Without Invoice'), ('invoice', 'Against Invoice'), ], default='invoice', required=True)
    partner_id = fields.Many2one('res.partner', 'Customer', required=True)
    delivery_address_id = fields.Many2one(related='picking_id.partner_id', string='Delivery Address')
    invoice_address_id = fields.Many2one(related='invoice_id.partner_id', string='Invoice Address')
    invoice_id = fields.Many2one('account.move', 'Invoice', copy=False, tracking=True)
    receipt_no = fields.Char('Receipt No', copy=False)
    journal_id = fields.Many2one('account.journal', 'Use Specific Journal', tracking=True)

    picking_id = fields.Many2one('stock.picking', 'Delivery', copy=False, tracking=True)
    sale_id = fields.Many2one('sale.order', 'Sales', copy=False, tracking=True)

    company_id = fields.Many2one("res.company", default=lambda self: self.env.company.id)
    line_ids = fields.One2many('sales.return.form.line', 'parent_id', string='Products', copy=False, auto_join=True)
    invoice_ids = fields.Many2many('account.move', string='Credit Notes', copy=False,
                                   domain=[('move_type', '=', 'out_refund')])
    picking_ids = fields.Many2many('stock.picking', string='Returned Deliveries', copy=False)
    scrap_ids = fields.Many2many('stock.scrap', string='Scrapped Products', copy=False)
    currency_id = fields.Many2one('res.currency', ondelete="restrict",
                                  default=lambda self: self.env.company.currency_id.id, copy=False)
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, compute='_amount_all', tracking=5)
    amount_tax = fields.Monetary(string='Tax Amount', store=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, compute='_amount_all', tracking=4,
                                   digits='Product Price')
    picking_type_id = fields.Many2one('stock.picking.type', 'Operation Type',
                                      domain="['|',('warehouse_id', '=', False), ('warehouse_id.company_id', '=', company_id), ('code', '=', 'incoming')]")
    reason_code_id = fields.Many2one('sales.return.reason.code', 'Reason Code')
    notes = fields.Text('Additional Notes')
    reason = fields.Text('Reason for Return')
    sr_attach_id = fields.Many2many('ir.attachment', 'sr_attach_rel', 'doc_id_sr', 'attach_id_sr',
                                     string="Attachment",
                                     copy=False)

    _sql_constraints = [
        ("name_uniq", "unique(name, company_id)", "Sales return form reference must be unique per company.")]

    def receipt_no_validation(self):
        if self.receipt_no:
            sales_return = self.search([('receipt_no', '=', self.receipt_no), ('type', '=', 'normal')])
            if len(sales_return) > 1:
                raise ValidationError('A sales return with the entered receipt number exists in the system')

    @api.onchange('receipt_no')
    def onchange_receipt_no(self):
        self.receipt_no_validation()

    @api.onchange('type')
    def onchange_picking_type_id(self):
        for rec in self:
            picking_type_id = self.env['stock.picking.type'].search(
                ['|', ('warehouse_id', '=', False), ('warehouse_id.company_id', '=', rec.company_id.id),
                 ('code', '=', 'incoming'), ('name', '=', 'Returns')])
            if rec.type == 'invoice':
                rec.picking_type_id = picking_type_id
            else:
                rec.picking_type_id = False

    @api.onchange('invoice_id')
    def onchange_journal_id(self):
        for rec in self:
            if rec.type == 'invoice':
                rec.journal_id = rec.invoice_id.journal_id

    @api.constrains('receipt_no')
    def _check_receipt_no(self):
        self.receipt_no_validation()

    @api.depends('line_ids.price_total')
    def _amount_all(self):
        """
        Compute the total amounts.
        """
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.line_ids:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })

    @api.onchange('type')
    def _onchange_type(self):
        self.update({
            'sale_id': False,
            'picking_id': False,
            'line_ids': False,
        })

    @api.onchange('reason_code_id')
    def _onchange_reason_code_id(self):
        if self.reason_code_id:
            self.line_ids.update({
                'reason_code_id': self.reason_code_id.id
            })

    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):
        if self.invoice_id:
            self.line_ids = False
            lines = []
            for line in self.invoice_id.invoice_line_ids:
                lot_list = line._get_invoiced_lot_values_by_product_sales_return(line.product_id.id)
                if lot_list:
                    for el in lot_list:
                        # lot = self.env['stock.lot'].search([('id', '=', el['lot_id'])])
                        lot = self.env['stock.lot'].browse(el['lot_id'])
                        el_qty = el['quantity']
                        #product_uom_qty = el_qty * line.package_id.qty
                        product_uom_qty = el_qty
                        lines.append((0, 0, {
                            'invoice_line_id': line.id,
                            'product_id': line.product_id.id,
                            'name': line.name,
                            'product_packaging_id': line.package_id.id,
                            'product_packaging_qty': el_qty/line.package_id.qty,
                            'pkg_unit_price': line.pkg_unit_price,
                            'price_unit': line.price_unit,
                            'tax_id': [(6, 0, line.tax_ids.ids)],
                            'product_uom_qty': product_uom_qty,
                            'product_uom': line.product_uom_id.id,
                            'lot_id': lot.id,
                            # Cha Change 12/10/2022
                            'dest_location_id': el['location_id']
                        }))
                else:
                    lines.append((0, 0, {
                        'invoice_line_id': line.id,
                        'product_id': line.product_id.id,
                        'name': line.name,
                        'product_packaging_id': line.package_id.id,
                        'product_packaging_qty': line.product_packaging_qty,
                        'pkg_unit_price': line.pkg_unit_price,
                        'price_unit': line.price_unit,
                        'tax_id': [(6, 0, line.tax_ids.ids)],
                        'product_uom_qty': line.quantity,
                        'product_uom': line.product_uom_id.id,
                    }))

            # print(errrr)
            sales = self.env['sale.order'].search([('invoice_ids', 'in', self.invoice_id.ids)])
            picking_id = False
            if sales:
                picking_id = sales[0].picking_ids[0] if sales[0].picking_ids.filtered(
                    lambda l: l.state == 'done') else False
            self.update({
                'line_ids': lines,
                'partner_id': self.invoice_id.partner_id.id,
                'sale_id': sales[0] if sales else False,
                'picking_id': picking_id,
            })
        else:
            self.update({
                'sale_id': False,
                'picking_id': False,
            })

    def action_request(self):
        if self.invoice_id and self.partner_id.id != self.invoice_id.partner_id.id:
            raise UserError(_("Selected customer and the customer in the invoice should be same."))
        self._check_qty_exceed()
        self.write({"state": "request"})

    def action_approve(self):
        reverse_moves = self.create_credit_note()
        self.create_picking()

        #Reconsile with invoice
        need_to_reconcile = not self.currency_id.is_zero(self.invoice_id.amount_residual)
        if need_to_reconcile and self.type == 'invoice':
            lines = self.invoice_id.mapped('line_ids')
            # Avoid maximum recursion depth.
            if lines:
                lines.remove_move_reconcile()
            reverse_moves.action_post()
            for move, reverse_move in zip(self.invoice_id, reverse_moves):
                lines = move.line_ids.filtered(
                    lambda x: (x.account_id.reconcile or x.account_id.account_type == 'asset_cash')
                              and not x.reconciled
                )
                for line in lines:
                    counterpart_lines = reverse_move.line_ids.filtered(
                        lambda x: x.account_id == line.account_id
                                  and x.currency_id == line.currency_id
                                  and not x.reconciled
                    )
                    (line + counterpart_lines).with_context(move_reverse_cancel=need_to_reconcile).reconcile()

            self.reconcile_rebates_against_invoice(self.invoice_id, reverse_moves)

        self.write({
            "state": "approve",
            "approve_user_id": self.env.user.id,
        })

    def reconcile_rebates_against_invoice(self, invoice, credit_note):

        return True

        #if return is against invoice,  reconcile rebate generated from invoice and rebate generated from credit note

        #Checking rebates from invoice is reconciled or not?

        journal_id = self.env['ir.config_parameter'].sudo().get_param('kg_sarya_rebate.rebate_journal_id', False)
        print("5>>>>>>>>>>>>>>>>>>>>>>>>>>")
        if not journal_id:
            raise UserError(_("You must configure journal for rebate in settings"))
        journal_id = int(journal_id)

        # Rebate from Invoice
        rebate_from_invoice = self.env['account.move'].search([('journal_id', '=', journal_id),
                                                               ('fixed_rebate_move_id', '=', invoice.id),
                                                               ('state', '=', 'posted')])

        if not rebate_from_invoice:
            return True

        #Rebate from Credit Note
        rebate_from_credit_note = self.env['account.move'].search([('journal_id', '=', journal_id),
                                                               ('fixed_rebate_move_id', '=', credit_note.id),
                                                               ('state', '=', 'posted')])

        if not rebate_from_credit_note:
            return True

        #check rebate entries is reconciled?

        lines = rebate_from_invoice.line_ids.filtered(
            lambda x: (x.account_id.reconcile or x.account_id.account_type == 'asset_cash')
                      and not x.reconciled
        )

        counterpart_lines = rebate_from_credit_note.line_ids.filtered(
            lambda x: (x.account_id.reconcile or x.account_id.account_type == 'asset_cash')
                      and not x.reconciled
        )

        #Reconcile if matching counter part entry found on credit not
        if lines and counterpart_lines:
            to_reconcile = (lines + counterpart_lines)
            to_reconcile.reconcile()


    def action_reject(self):
        self.write({"state": "reject"})

    def action_draft(self):
        self.write({"state": "draft"})

    def action_cancel(self):
        self.write({"state": "cancel", "approve_user_id": False})

    def action_done(self):
        self.write({"state": "done"})
        return True

    def _check_qty_exceed(self):
        if self.type == 'invoice':
            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            for line in self.line_ids:
                lines = self.line_ids.filtered(lambda l: l.invoice_line_id.id == line.invoice_line_id.id)
                invoice_qty = sum(lines.mapped('invoice_line_id.quantity'))
                line_qty = 0.0
                for ln in lines:
                    qty = ln.product_uom._compute_quantity(ln.product_uom_qty, ln.invoice_line_id.product_uom_id)
                    line_qty += qty
                if float_compare(line_qty, invoice_qty, precision_digits=precision) > 0:
                    raise UserError(
                        _("Quantity for the product/description '%s' shouldn't be exceeded than it's invoice qty") % line.invoice_line_id.name)

    def create_credit_note(self):
        if not self.company_id.acc_sales_return_id:
            raise ValidationError(_('Add Sales Return Account in Account Module Configuration Settings'))
        sales_return_id = self.company_id.acc_sales_return_id
        self.ensure_one()
        reverse_moves = self.invoice_id.reversal_move_id.filtered(lambda l: l.state == 'posted')
        if self.type == 'invoice' and reverse_moves and False:
            raise UserError(_("A credit note(%s) is already created for the invoice %s") % (
                ', '.join(reverse_moves.mapped('name')), self.invoice_id.name))
        self._check_qty_exceed()
        invoice_lines = []
        for line in self.line_ids:
            invoice_lines.append((0, 0, line._prepare_invoice_line()))
        invoice_vals = self._prepare_invoice()
        invoice_vals.update({
            'invoice_line_ids': invoice_lines
        })
        reverse_moves = self.env['account.move'].create(invoice_vals)
        journal_line_id = reverse_moves.line_ids
        for account in reverse_moves.invoice_line_ids:
            account.account_id = sales_return_id
        for move, reverse_move in zip(self.invoice_id, reverse_moves.with_context(check_move_validity=False)):
            # Update amount_currency if the date has changed.
            if move.date != reverse_move.date:
                for line in reverse_move.line_ids:
                    if line.currency_id and False:
                        line._onchange_currency()
            reverse_moves._sync_dynamic_lines({'records': reverse_move})
        reverse_moves._check_balanced({'records': reverse_moves})



        self.invoice_ids |= reverse_moves
        if self.type == 'invoice':
            self.invoice_id.write({
                'reversal_move_id': [(6, 0, reverse_moves.ids)]
            })
            reverse_moves.write({
                'reversed_entry_id': self.invoice_id.id
            })
        return reverse_moves

    def _prepare_invoice(self):
        self.ensure_one()
        journal = self.journal_id
        if not journal:
            raise UserError(_('Please select journal on retrun'))

        invoice_vals = {
            'ref': self.receipt_no,
            'move_type': 'out_refund',
            'currency_id': self.currency_id.id,
            'user_id': self.user_id.id,
            'invoice_user_id': self.user_id.id,
            'partner_id': self.invoice_address_id.id or self.partner_id.id,
            'journal_id': journal.id,
            'invoice_origin': self.name,
            'narration': self.reason,
            'company_id': self.company_id.id,
            'invoice_date': self.credit_note_date,
            'sale_order_id': self.sale_id.id,
            'sale_order_customer_id': self.sale_id.partner_id.id if self.sale_id else self.invoice_address_id.id or self.partner_id.id
        }
        partner_id = self.invoice_address_id or self.partner_id

        if self.type == 'normal':
            if self.partner_id.parent_customer_id and \
               self.partner_id.master_parent_id and \
               self.partner_id.master_parent_id.name not in ['Shaklan', 'Lulu']:
                invoice_vals['partner_id'] = self.partner_id.parent_customer_id.id
                invoice_vals['partner_shipping_id'] = self.partner_id.id
                partner_id = self.partner_id.parent_customer_id
            else:
                invoice_vals['partner_shipping_id'] = self.partner_id.id
        else:
            invoice_vals['partner_shipping_id'] = self.delivery_address_id.id
        if partner_id:
            invoice_vals['invoice_payment_term_id'] = partner_id.property_payment_term_id.id

        print("\n\n\ninvoice_vals ==>> ", invoice_vals)

        return invoice_vals

    def create_picking(self):
        self.ensure_one()
        if not self.picking_type_id:
            ccccccccccccccccccc
            raise UserError(_("You must select an operation type."))
        self._check_qty_exceed()
        picking_vals = self._prepare_picking()
        new_picking_id = self.env['stock.picking'].create(picking_vals)

        for line in self.line_ids:
            move_vals = line._prepare_picking_line(new_picking_id)
            self.env['stock.move'].create(move_vals)

        self.sale_id.write({
            'picking_ids': [(4, 0, new_picking_id.ids)]
        })

        new_picking_id.action_confirm()
        new_picking_id.button_validate()

        #self.create_scrap(new_picking_id)
        self.picking_ids |= new_picking_id
        return self.action_view_pickings()

    def create_scrap(self, picking_id=False):
        if self.scrap_ids:
            raise UserError(_("Some scrap moves are already created."))
        picking = picking_id or self.picking_ids.filtered(lambda l: l.state == 'done')
        if picking:
            for line in self.line_ids.filtered(lambda l: l.stock_type == 'out'):
                if line.product_uom_qty:
                    scrap = self.env['stock.scrap'].create({
                        'picking_id': picking.id,
                        'product_id': line.product_id.id,
                        'product_uom_id': line.product_uom.id,
                        'scrap_qty': line.product_uom_qty,
                        'lot_id': line.lot_id.id,
                    })
                    scrap._onchange_picking_id()
                    scrap._onchange_product_id()
                    scrap.action_validate()
                    self.scrap_ids |= scrap
                    new_refs = [
                        "<a href=# data-oe-model=stock.scrap data-oe-id=%s>stock scrap</a>" % scrap.id]
                    message = _("A new %s has been created") % ','.join(new_refs)
                    self.message_post(body=message)
        else:
            raise UserError(_("There is nothing to scrap."))

    def action_view_invoices(self):
        action = self.env.ref("account.action_move_out_refund_type").sudo().read()[0]
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
        action["context"] = {}
        picking_ids = self.picking_ids
        if len(picking_ids) > 1:
            action["domain"] = [("id", "in", picking_ids.ids)]
        elif picking_ids:
            action["views"] = [(self.env.ref("stock.view_picking_form").id, "form")]
            action["res_id"] = picking_ids.id
        return action

    def action_view_scraps(self):
        action = self.env.ref("stock.action_stock_scrap").sudo().read()[0]
        action["context"] = {}
        scrap_ids = self.scrap_ids
        if len(scrap_ids) > 1:
            action["domain"] = [("id", "in", scrap_ids.ids)]
        elif scrap_ids:
            action["views"] = [(self.env.ref("stock.stock_scrap_form_view").id, "form")]
            action["res_id"] = scrap_ids.id
        return action

    @api.model
    def create(self, vals):
        vals["name"] = self.env["ir.sequence"].next_by_code("sales.return.form")
        return super(SalesReturnForm, self).create(vals)

    def unlink(self):
        if self.filtered(lambda r: r.state not in ('draft', 'request')):
            raise UserError(_("Only requests on draft/approve status can be deleted"))
        return super(SalesReturnForm, self).unlink()

    def _prepare_picking(self):
        if not self.partner_id.property_stock_supplier.id:
            raise UserError(_("You must set a Vendor Location for this partner %s", self.partner_id.name))
        if not self.invoice_id and self.type == 'invoice':
            raise UserError(
                _("You must select an invoice to create a delivery return or change return type.") % self.invoice_id.name)
        if not self.sale_id and self.type == 'invoice':
            raise UserError(_("There is no sales related to the invoice %s") % self.invoice_id.name)
        vals = {
            'picking_type_id': self.picking_type_id.id,
            'partner_id': self.delivery_address_id.id or self.partner_id.id,
            'user_id': False,
            'date': self.date,
            'origin': self.name,
            'sale_id': self.sale_id.id,
            'location_dest_id': self.picking_type_id.default_location_dest_id.id,
            'location_id': self.partner_id.property_stock_customer.id,
            'company_id': self.company_id.id,
            'group_id': self.sale_id.procurement_group_id.id,
        }

        return vals


class SalesReturnFormLine(models.Model):
    _name = "sales.return.form.line"
    _description = "Sales Return Form Line"

    parent_id = fields.Many2one('sales.return.form', string='Parent', required=True, ondelete='cascade', index=True,
                                copy=False)
    name = fields.Char(string='Description', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    invoice_id = fields.Many2one(related='parent_id.invoice_id')
    invoice_line_id = fields.Many2one('account.move.line', 'Invoice Description', copy=False,
                                      domain="[('move_id', '=', invoice_id)]")

    price_unit = fields.Float('Unit Price', required=True, digits='Product Price', default=0.0)

    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Total Tax', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)

    tax_id = fields.Many2many('account.tax', string='Taxes',
                              domain=['|', ('active', '=', False), ('active', '=', True)])

    discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)

    product_id = fields.Many2one(
        'product.product', string='Product',
        domain="[('sale_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        change_default=True, ondelete='restrict', check_company=True)
    product_template_id = fields.Many2one(
        'product.template', string='Product Template',
        related="product_id.product_tmpl_id", domain=[('sale_ok', '=', True)])
    product_uom_qty = fields.Float(string='Qty', digits='Product Unit of Measure', required=True, default=1.0)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure',
                                  domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')

    currency_id = fields.Many2one(related='parent_id.currency_id', depends=['parent_id.currency_id'], store=True,
                                  string='Currency')
    company_id = fields.Many2one(related='parent_id.company_id', string='Company', store=True, index=True)
    product_packaging_id = fields.Many2one('product.packaging', string='Packaging', default=False,
                                           domain="[('sales', '=', True), ('product_id','=',product_id)]",
                                           check_company=True)
    product_packaging_qty = fields.Float('Pkg Qty')
    invoice_packaging_qty = fields.Float(related='invoice_line_id.product_packaging_qty', string='Invoice Pkg Qty')
    invoice_packaging_id = fields.Many2one(related='invoice_line_id.package_id', string='Invoice Pkg')
    pkg_unit_price = fields.Float('Pkg Price')
    stock_type = fields.Selection(string='Stock (IN/OUT)', selection=[('in', 'In'), ('out', 'Out'), ], default='in',
                                  required=True)
    lot_id = fields.Many2one(
        'stock.lot', 'Lot/Serial No.',
        domain="[('product_id', '=', product_id), ('company_id', '=', company_id)]", check_company=True)
    expiration_date = fields.Datetime(string='Expiration Date', related='lot_id.expiration_date')
    has_tracking = fields.Selection(related='product_id.tracking', string='Product with Tracking')
    reason_code_id = fields.Many2one('sales.return.reason.code', 'Reason Code')
    type = fields.Selection(related='parent_id.type')

    # Cha Change 12/10/2022
    dest_location_id = fields.Many2one('stock.location', 'Location', domain="[('usage', '=', 'internal')]")

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the line.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.parent_id.currency_id, line.product_uom_qty,
                                            product=line.product_id, partner=line.parent_id.partner_id)
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    @api.onchange('invoice_line_id')
    def onchange_invoice_line_id(self):
        if self.invoice_line_id:
            self.update({
                'product_id': self.invoice_line_id.product_id.id,
                'name': self.invoice_line_id.name,
                'product_packaging_id': self.invoice_line_id.package_id.id,
                'product_packaging_qty': self.invoice_line_id.product_packaging_qty,
                'pkg_unit_price': self.invoice_line_id.pkg_unit_price,
                'price_unit': self.invoice_line_id.price_unit,
                'tax_id': self.invoice_line_id.tax_ids,
                'product_uom_qty': self.invoice_line_id.quantity,
                'product_uom': self.invoice_line_id.product_uom_id.id,
            })

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.parent_id.type == 'normal':
            if self.product_id:
                self.product_uom = self.product_id.uom_id.id
            else:
                self.product_uom = False

    @api.onchange('reason_code_id')
    def onchange_reason_code_id(self):
        if self.reason_code_id:
            self.update({
                'stock_type': self.reason_code_id.stock_type
            })

    @api.onchange('product_packaging_id')
    def _onchange_product_packaging_id(self):
        date_today = date.today()
        if self.product_packaging_id:
            if self.parent_id.type == 'normal':
                records = self.parent_id.partner_id.property_product_pricelist.item_ids.filtered(lambda  l: l.product_tmpl_id == self.product_id.product_tmpl_id
                                            and l.packging_id == self.product_packaging_id)
                for record in records:
                    if record.date_start and record.date_end:
                        if record.date_start.date() <= date_today <= record.date_end.date():
                            self.pkg_unit_price = record.final_price
                            break
                        else:
                            continue
                    else:
                        self.pkg_unit_price = record.final_price
            self.product_uom_qty = self.product_packaging_id.qty * self.product_packaging_qty

    @api.onchange('product_uom', 'product_uom_qty')
    def _onchange_update_product_packaging_qty(self):
        if not self.product_packaging_id:
            self.product_packaging_qty = 0.0
        else:
            packaging_uom = self.product_packaging_id.product_uom_id
            packaging_uom_qty = self.product_uom._compute_quantity(self.product_uom_qty, packaging_uom)
            self.product_packaging_qty = float_round(packaging_uom_qty / self.product_packaging_id.qty,
                                                     precision_rounding=packaging_uom.rounding)

    @api.onchange('product_packaging_qty')
    def _onchange_product_packaging_qty(self):
        if self.product_packaging_id:
            packaging_uom = self.product_packaging_id.product_uom_id
            qty_per_packaging = self.product_packaging_id.qty
            product_uom_qty = packaging_uom._compute_quantity(self.product_packaging_qty * qty_per_packaging,
                                                              self.product_uom)
            if float_compare(product_uom_qty, self.product_uom_qty, precision_rounding=self.product_uom.rounding) != 0:
                self.product_uom_qty = product_uom_qty

    @api.onchange('product_packaging_qty', 'product_packaging_id', 'pkg_unit_price')
    def _onchange_pkg_qty(self):
        if self.pkg_unit_price and self.product_packaging_id:
            self.price_unit = self.pkg_unit_price / self.product_packaging_id.qty
        elif self.pkg_unit_price == 0:
            self.price_unit = 0.0

    @api.onchange('product_id')
    def product_id_change(self):
        if not self.product_id:
            return
        vals = {}
        if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
            vals['product_uom'] = self.product_id.uom_id
            vals['product_uom_qty'] = self.product_uom_qty or 1.0

        product = self.product_id.with_context(
            lang=get_lang(self.env, self.parent_id.partner_id.lang).code,
            partner=self.parent_id.partner_id,
            quantity=vals.get('product_uom_qty') or self.product_uom_qty,
            date=self.parent_id.date,
            pricelist=self.parent_id.partner_id.property_product_pricelist.id,
            uom=self.product_uom.id
        )

        vals.update(name=self.product_id.get_product_multiline_description_sale())

        self.update(vals)

    @api.onchange('product_packaging_id')
    def package_onchange(self):
        if self.product_packaging_id:
            package_id = self.product_packaging_id.id
            for i in self.product_id.packaging_ids:
                if package_id == i.id:
                    self.name = str(i.barcode) + '-' + str(i.description)

    @api.onchange('product_uom', 'product_uom_qty')
    def product_uom_change(self):
        if not self.product_uom or not self.product_id:
            self.price_unit = 0.0

    def _prepare_invoice_line(self, **optional_values):
        """
        Prepare the dict of values to create the new invoice line.
        """

        self.ensure_one()
        res = {
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'quantity': self.product_uom_qty,
            'package_id': self.product_packaging_id.id,
            'product_packaging_qty': self.product_packaging_qty,
            'pkg_unit_price': self.pkg_unit_price,
            'sale_line_ids': [(6, 0, self.invoice_line_id.sale_line_ids.ids)],
            'price_unit': self.price_unit,
            'tax_ids': [(6, 0, self.tax_id.ids)],
            'sales_return_line_id' : self.id
        }
        return res

    def _prepare_picking_line(self, picking):
        """
        Prepare the dict of values to create the new stock move.
        """

        self.ensure_one()
        product = self.product_id.with_context(lang=self.parent_id.partner_id.lang or self.env.user.lang)
        date_planned = self.parent_id.date
        price_unit = self._get_stock_move_price_unit()
        stock_move = False
        if self.invoice_id.move_type == 'out_invoice':
            stock_move = self.invoice_line_id.sale_line_ids.mapped('move_ids').filtered(
                lambda x: x.state == 'done' and x.location_dest_id.usage == 'customer')

        move_line = [(0, 0, {
                'lot_id': self.lot_id.id,
                'picking_id': picking.id,
                'product_id': self.product_id.id,
                'quantity': self.product_uom_qty,
                'lot_name': self.lot_id.name,
                'product_uom_id': self.product_uom.id,
                'location_id': self.parent_id.partner_id.property_stock_customer.id,
                'location_dest_id':  self.dest_location_id and self.dest_location_id.id or \
                                self.parent_id.picking_type_id.default_location_dest_id.id
            })]


        return {
            'name': (self.name or '')[:2000],
            'product_id': self.product_id.id,
            'date': date_planned,
            'date_deadline': date_planned,
            'location_id': self.parent_id.partner_id.property_stock_customer.id,
            'location_dest_id': self.dest_location_id and self.dest_location_id.id or \
                                self.parent_id.picking_type_id.default_location_dest_id.id,
            'picking_id': picking.id,
            'origin_returned_move_id': stock_move and stock_move[0].id or False,
            'group_id': self.parent_id.sale_id.procurement_group_id.id,

            'partner_id': self.parent_id.partner_id.id,
            'state': 'assigned',
            'company_id': self.parent_id.company_id.id,
            'price_unit': price_unit,
            'picking_type_id': self.parent_id.picking_type_id.id,
            'origin': self.parent_id.name,
            'description_picking': product.description_pickingin or self.name,
            'warehouse_id': self.parent_id.picking_type_id.warehouse_id.id,
            'product_uom_qty': self.product_uom_qty,
            'product_uom': self.product_uom.id,
            'product_packaging_id': self.product_packaging_id.id,
            'pkg_demand': self.product_packaging_qty if self.product_packaging_qty else 0.0,
            'pkg_done': self.product_packaging_qty if self.product_packaging_qty else 0.0,
            'sale_line_id': self.invoice_line_id.sale_line_ids[0].id if self.invoice_line_id.sale_line_ids else False,
            'to_refund': True,
            'sales_return_line_id': self.id,
            'move_line_ids': move_line
        }


    def _get_stock_move_price_unit(self):
        """CHANDHU :: Logic for getting cost price is wrong, It was taking sale price for the stock valuation also"""
        self.ensure_one()
        price_unit = 0

        #Getting Puchase Value
        stock_valuation = self.env['stock.valuation.layer'].sudo().with_context(active_test=False).search([
            ('product_id', '=', self.product_id.id),
            ('company_id', '=', self.parent_id.company_id.id),
            ('lot_id', '=', self.lot_id.id)], order='create_date, id')
        if stock_valuation:
            purchase_stock_valuation = stock_valuation[0]
            value = purchase_stock_valuation.value
            quantity = purchase_stock_valuation.quantity

            if not purchase_stock_valuation.stock_move_id:
                return price_unit
            if not purchase_stock_valuation.stock_move_id.origin:
                return price_unit
            if 'P0' not in purchase_stock_valuation.stock_move_id.origin:
                return price_unit

            # Adding landed cost to Purchase Value
            domain = [
                ('company_id', '=', self.parent_id.company_id.id),
                ('product_id', '=', self.product_id.id),
                ('lot_id', '=', self.lot_id.id),
                ('quantity', '=', 0),
                ('unit_cost', '=', 0),
                ('create_date', '>=', purchase_stock_valuation.create_date),
                ('stock_landed_cost_id', '!=', False)
            ]
            all_candidates = self.env['stock.valuation.layer'].sudo().search(domain)
            for candidate in all_candidates:
                value += candidate.value

            #Getting unit price by dividing total value and total quantity
            if quantity > 0.001:
                price_unit = value/quantity
        return price_unit
