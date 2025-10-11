# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_date

from twilio.rest import Client
import json

class AccountMove(models.Model):
    _inherit = 'account.move'

    verified_for_reconcile =  fields.Boolean(string="Verify For Reconciliation", default=False)
    verified_for_reconcile_by = fields.Many2one('res.users', string='Verified By')
    marchandiser_id = fields.Many2one(related="partner_id.marchandiser_id", store=True, readonly=True)
    invoice_emailed_date = fields.Datetime("Invoice Emailed Date")
    total_product_weight = fields.Float(string="Total Weight", compute="_compute_total_product_weight")
    total_product_gross_weight = fields.Float(string="Total Weight", compute="_compute_total_product_weight")

    ready_to_generate_ewaybill = fields.Boolean("Ready to generate eWayBill")

    tax_data_text = fields.Char(string="Tax Data Text", compute="_compute_tax_data_text")

    tax_sgst = fields.Float(string="Tax Data SGST", compute="_compute_tax_data_text")
    tax_cgst = fields.Float(string="Tax Data CGST", compute="_compute_tax_data_text")
    tax_igst = fields.Float(string="Tax Data IGST", compute="_compute_tax_data_text")
    tax_cess = fields.Float(string="Tax Data CESS", compute="_compute_tax_data_text")
    tax_gst = fields.Float(string="Tax Data GST", compute="_compute_tax_data_text")
    tax_exempt = fields.Float(string="Tax Data Exempt", compute="_compute_tax_data_text")
    tax_nil_rated = fields.Float(string="Tax Data Nil Rated", compute="_compute_tax_data_text")
    tax_non_gst_supplies = fields.Float(string="Tax Data Non GST Supplies", compute="_compute_tax_data_text")
    tax_tcs = fields.Float(string="Tax Data TCS", compute="_compute_tax_data_text")
    tax_tds = fields.Float(string="Tax Data TDS", compute="_compute_tax_data_text")
    transport_id = fields.Char("Transporter ID", copy=False, tracking=True)

    def _compute_tax_data_text(self):
        for move in self:
            tax_data = ""
            tax_sgst = 0
            tax_cgst = 0
            tax_igst = 0
            tax_cess = 0
            tax_gst = 0
            tax_exempt = 0
            tax_nil_rated = 0
            tax_non_gst_supplies = 0
            tax_tcs = 0
            tax_tds = 0

            if move.is_invoice(include_receipts=True):
                base_lines = move.invoice_line_ids.filtered(lambda line: line.display_type == 'product')
                base_line_values_list = [line._convert_to_tax_base_line_dict() for line in base_lines]
                sign = move.direction_sign
                if move.id:
                    # The invoice is stored so we can add the early payment discount lines directly to reduce the
                    # tax amount without touching the untaxed amount.
                    base_line_values_list += [
                        {
                            **line._convert_to_tax_base_line_dict(),
                            'handle_price_include': False,
                            'quantity': 1.0,
                            'price_unit': sign * line.amount_currency,
                        }
                        for line in move.line_ids.filtered(lambda line: line.display_type == 'epd')
                    ]

                kwargs = {
                    'base_lines': base_line_values_list,
                    'currency': move.currency_id or move.journal_id.currency_id or move.company_id.currency_id,
                }

                if move.id:
                    kwargs['tax_lines'] = [
                        line._convert_to_tax_line_dict()
                        for line in move.line_ids.filtered(lambda line: line.display_type == 'tax')
                    ]
                else:
                    # In case the invoice isn't yet stored, the early payment discount lines are not there. Then,
                    # we need to simulate them.
                    epd_aggregated_values = {}
                    for base_line in base_lines:
                        if not base_line.epd_needed:
                            continue
                        for grouping_dict, values in base_line.epd_needed.items():
                            epd_values = epd_aggregated_values.setdefault(grouping_dict, {'price_subtotal': 0.0})
                            epd_values['price_subtotal'] += values['price_subtotal']

                    for grouping_dict, values in epd_aggregated_values.items():
                        taxes = None
                        if grouping_dict.get('tax_ids'):
                            taxes = self.env['account.tax'].browse(grouping_dict['tax_ids'][0][2])

                        kwargs['base_lines'].append(self.env['account.tax']._convert_to_tax_base_line_dict(
                            None,
                            partner=move.partner_id,
                            currency=move.currency_id,
                            taxes=taxes,
                            price_unit=values['price_subtotal'],
                            quantity=1.0,
                            account=self.env['account.account'].browse(grouping_dict['account_id']),
                            analytic_distribution=values.get('analytic_distribution'),
                            price_subtotal=values['price_subtotal'],
                            is_refund=move.move_type in ('out_refund', 'in_refund'),
                            handle_price_include=False,
                        ))
                kwargs['is_company_currency_requested'] = move.currency_id != move.company_id.currency_id
                tax_totals = self.env['account.tax']._prepare_tax_totals(**kwargs)


                print("\n\n\ntax_totals ==============>>>> ", tax_totals)
                for groups_by_subtotal in tax_totals.get('groups_by_subtotal', []):
                    for untaxed_amount in tax_totals['groups_by_subtotal'][groups_by_subtotal]:
                        tax_data += "%s: %s, " % (untaxed_amount.get('tax_group_name', ''), str(untaxed_amount.get('tax_group_amount', '0.00')))

                        tax_group_name = untaxed_amount.get('tax_group_name', '')
                        tax_group_amount = untaxed_amount.get('tax_group_amount', 0.00)

                        if tax_group_name == 'SGST':
                            tax_sgst += tax_group_amount
                        elif tax_group_name == 'CGST':
                            tax_cgst += tax_group_amount
                        elif tax_group_name == 'IGST':
                            tax_igst += tax_group_amount
                        elif tax_group_name == 'CESS':
                            tax_cess += tax_group_amount
                        elif tax_group_name == 'GST':
                            tax_gst += tax_group_amount
                        elif tax_group_name == 'Exempt':
                            tax_exempt += tax_group_amount
                        elif tax_group_name == 'Nil Rated':
                            tax_nil_rated += tax_group_amount
                        elif tax_group_name == 'Non GST Supplies':
                            tax_non_gst_supplies += tax_group_amount
                        elif tax_group_name == 'TCS':
                            tax_tcs += tax_group_amount
                        elif tax_group_name == 'TDS':
                            tax_tds += tax_group_amount




            move.tax_data_text = tax_data
            move.tax_sgst = tax_sgst
            move.tax_cgst = tax_cgst
            move.tax_igst = tax_igst
            move.tax_cess = tax_cess
            move.tax_gst = tax_gst
            move.tax_exempt = tax_exempt
            move.tax_nil_rated = tax_nil_rated
            move.tax_non_gst_supplies = tax_non_gst_supplies
            move.tax_tcs = tax_tcs
            move.tax_tds = tax_tds


    def send_notification(self, employee_ids, message, subject, button_url):

        for employee_id in employee_ids:
            # Email notification
            mail_content = "Dear " + str(employee_id.name)
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


    def set_ready_to_generate_ewaybill(self):
        self.ready_to_generate_ewaybill = True
        users = self.env.ref('cha_sarya_account.can_process_ewaybill').users
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
                message = "Hi %s, Please process eWayBill for Invoice %s" % (
                    employee.name, self.name)
                subject = "India: eWayBill generation pending : %s" % self.name
                button_url = "#id=%s&cids=1&menu_id=709&action=1060&model=account.move&view_type=form" % (str(self.id))
                self.send_notification(employees, message, subject, button_url)


    def _compute_total_product_weight(self):
        for move in self:
            weight, gross_weight = 0, 0
            for line in move.invoice_line_ids:
                if line.product_id and line.package_id:
                    pack_qty = line.package_id.qty
                    weight += (line.product_id.weight)*pack_qty*line.product_packaging_qty
                    gross_weight += (line.product_id.gross_weight)*pack_qty*line.product_packaging_qty
            move.total_product_weight = weight
            move.total_product_gross_weight = gross_weight


    def write(self, values):
        res = super(AccountMove, self).write(values)
        if 'verified_for_reconcile' in values:
            for mv in self:
                if mv.verified_for_reconcile:
                    mv.verified_for_reconcile_by = self.env.uid
                else:
                    mv.verified_for_reconcile_by = False
        return res


    def verified_move_for_reconcile(self):
        for mv in self:
            if mv.verified_for_reconcile:
                mv.verified_for_reconcile = False
            else:
                mv.verified_for_reconcile = True

    def verify_for_reconcile(self):
        self.verified_for_reconcile = True

    def remove_from_reconcile(self):
        self.verified_for_reconcile = False

    def reset_invoice_and_change_customer(self, new_partner):
        self.button_draft()
        if new_partner:
            partner_id = self.env['res.partner'].search([('cust_sequence', '=', new_partner)])
            if partner_id:
                partner_id = partner_id[0]
                self.partner_id = partner_id.id
        self.action_post()

    def xmlrpc_reset_invoice_and_change_customer(self, invoice_number, new_partner):
        if invoice_number and new_partner:
            invoice = self.search([('name', '=', invoice_number)])
            invoice.reset_invoice_and_change_customer(new_partner)
        return True

    def xmlrpc_invoice_repost_rebate(self, invoice_number):
        if invoice_number:
            invoice = self.search([('name', '=', invoice_number)])
            if invoice:
                invoice._unlink_existing_rebate_items()
                invoice._update_rebate_entries()
                invoice._cancel_fixed_rebate_moves()

                invoice.update_rebates()
        return True

    def check_stock_in_out(self):
        in_out_account_id = 539
        search_domain = [('account_id', '=', in_out_account_id),
                         ('date', '=', '16/11/2022')]
        move_lines = self.env['account.move.line'].search(search_domain)
        print('move_lines ====>> ', len(move_lines))


    def update_due_date(self, invoice_ids):
        # try to run all invoices
        #invoices = self.search([('move_type', 'in', ('out_invoice', 'out_refund'))])
        invoices = self.browse(invoice_ids)
        total_inv = len(invoices)
        count = 0
        for inv in invoices:
            count = count + 1
            print(total_inv, ' : ', count)
            inv.update_due_date_correction()
        return True

    def update_due_date_of_rebate(self, invoice_ids):
        invoices = self.browse(invoice_ids)
        total_inv = len(invoices)
        count = 0

        #Journal of move
        journal_id = self.env['ir.config_parameter'].sudo().get_param('kg_sarya_rebate.rebate_journal_id', False)
        print("2>>>>>>>>>>>>>>>>>>>>>>>>>>")
        if not journal_id:
            raise UserError(_("You must configure journal for rebate in settings"))
        journal_id = int(journal_id)

        for inv in invoices:
            count = count + 1
            print(total_inv, ' : ', count, " :: ", inv.id)

            rebate_search_condition = [('state', '=', 'posted'), ('journal_id', '=', journal_id),
                                       ('ref', 'ilike', inv.name)]

            rebate_move = self.env['account.move'].search(rebate_search_condition)

            actual_rebates = []

            print("rebate_move =======>> ", rebate_move)

            if rebate_move:
                for r_move in rebate_move:

                    if r_move.fixed_rebate_move_id:
                        if r_move.fixed_rebate_move_id.id == inv.id:
                            actual_rebates.append(r_move)

                    else:
                        r_move_ref = r_move.ref
                        s_r_move_ref = r_move_ref.split("-")
                        if len(s_r_move_ref) == 2:
                            s_r_move_ref = s_r_move_ref[1].strip()
                            if s_r_move_ref == inv.name:
                                actual_rebates.append(r_move)


            print("actual_rebates =====>> ", actual_rebates)
            for rebate in actual_rebates:
                others_lines = rebate.line_ids.filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))

                inv_lines = inv.line_ids.filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))
                invoice_date_due = False
                for inv_l in inv_lines:
                    invoice_date_due = inv_l.date_maturity

                others_lines.date_maturity = invoice_date_due
                rebate.invoice_date_due = invoice_date_due

        return True


    def update_due_date_correction(self):

        def _get_payment_terms_computation_date(self):
            ''' Get the date from invoice that will be used to compute the payment terms.
            :param self:    The current account.move record.
            :return:        A datetime.date object.
            '''

            return self.invoice_date


        def _compute_payment_terms(self, date, total_balance, total_amount_currency):
            if self.invoice_payment_term_id:
                to_compute = self.invoice_payment_term_id.compute(total_balance, date_ref=date, currency=self.company_id.currency_id)
                if self.currency_id == self.company_id.currency_id:
                    # Single-currency.
                    return [(b[0], b[1], b[1]) for b in to_compute]
                else:
                    # Multi-currencies.
                    to_compute_currency = self.invoice_payment_term_id.compute(total_amount_currency, date_ref=date, currency=self.currency_id)
                    return [(b[0], b[1], ac[1]) for b, ac in zip(to_compute, to_compute_currency)]
            else:
                return [(fields.Date.to_string(date), total_balance, total_amount_currency)]

        #update payment term form master
        self.invoice_payment_term_id = self.partner_id.property_payment_term_id

        computation_date = _get_payment_terms_computation_date(self)
        others_lines = self.line_ids.filtered(lambda line: line.account_id.account_type not in ('asset_receivable', 'liability_payable'))
        company_currency_id = (self.company_id or self.env.company).currency_id
        total_balance = sum(others_lines.mapped(lambda l: company_currency_id.round(l.balance)))
        total_amount_currency = sum(others_lines.mapped('amount_currency'))

        to_compute = _compute_payment_terms(self, computation_date, total_balance, total_amount_currency)

        if to_compute:
            due_date = to_compute[0][0]

            others_lines = self.line_ids.filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))
            others_lines.date_maturity = due_date
            self.invoice_date_due = due_date

    '''Override sequence mixin constraint to remove sequence check year wise.'''

    @api.constrains(lambda self: (self._sequence_field, self._sequence_date_field))
    def _constrains_date_sequence(self):
        # Make it possible to bypass the constraint to allow edition of already messed up documents.
        # /!\ Do not use this to completely disable the constraint as it will make this mixin unreliable.
        constraint_date = fields.Date.to_date(self.env['ir.config_parameter'].sudo().get_param(
            'sequence.mixin.constraint_start_date',
            '1970-01-01'
        ))
        for record in self:
            if not record._must_check_constrains_date_sequence():
                continue
            date = fields.Date.to_date(record[record._sequence_date_field])
            sequence = record[record._sequence_field]
            if (
                    sequence
                    and date
                    and date > constraint_date
                    and not record._sequence_matches_date()
            ):
                raise ValidationError(_(
                    "The %(date_field)s (%(date)s) doesn't match the sequence number of the related %(model)s (%(sequence)s)\n"
                    "You will need to clear the %(model)s's %(sequence_field)s to proceed.\n"
                    "In doing so, you might want to resequence your entries in order to maintain a continuous date-based sequence.",
                    date=format_date(self.env, date),
                    sequence=sequence,
                    date_field=record._fields[record._sequence_date_field]._description_string(self.env),
                    sequence_field=record._fields[record._sequence_field]._description_string(self.env),
                    model=self.env['ir.model']._get(record._name).display_name,
                ))

    def _must_check_constrains_date_sequence(self):
        return False

class AccountMoveLine(models.Model):

    _inherit = "account.move.line"
    _description = "Account Move Line"

    tax_amount = fields.Float(string="Tax Amount", compute="_compute_tax_amount")
    remove_vat_restriction = fields.Boolean()


    # Override from base to remove restriction on choosing receivable account in Vendor bill or debit note.
    @api.constrains('account_id', 'display_type')
    def _check_payable_receivable(self):
        for line in self:
            account_type = line.account_id.account_type
            if line.move_id.is_sale_document(include_receipts=True):
                if (line.display_type == 'payment_term') ^ (account_type == 'asset_receivable'):
                    raise UserError(_("Any journal item on a receivable account must have a due date and vice versa."))
            if line.move_id.is_purchase_document(include_receipts=True):
                pass
                # print('line.display_type', line.display_type)
                # print('account_type', account_type)
                # print((line.display_type == 'payment_term') ^ (account_type == 'liability_payable'))
                # if (line.display_type == 'payment_term') ^ (account_type == 'liability_payable'):
                #     raise UserError(_("Any journal item on a payable account must have a due date and vice versa."))

    @api.onchange("quantity", "tax_ids")
    def _compute_tax_amount(self):
        for move_line_id in self:
            if move_line_id.display_type == 'product':
                tax_only = 0
                price = move_line_id.price_unit * move_line_id.quantity
                # print('Dis', move_line_id.discount)
                if move_line_id.discount > 0:
                    price = move_line_id.price_unit * move_line_id.quantity * (move_line_id.discount*.01)
#                     print('price', price)
#                 print('price', price)
                for tax_id in move_line_id.tax_ids:
                    tax_only += price * (tax_id.amount / 100)
#                 print('tax_only', tax_only)
                move_line_id.tax_amount = tax_only
            else:
                move_line_id.tax_amount = 0

class AccountPayment(models.Model):
    _inherit = "account.payment"

    payment_amount_residual = fields.Monetary(string="Balance Amount", store=True,
                                      compute= '_compute_payment_amount_residual')

    @api.depends('move_id.line_ids.amount_residual', 'move_id.line_ids.amount_residual_currency',
                 'move_id.line_ids.account_id')
    def _compute_payment_amount_residual(self):
        for pay in self:
            amount_residual = 0
            residual_field = 'amount_residual' if pay.currency_id == pay.company_id.currency_id else 'amount_residual_currency'
            liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()
            reconcile_lines = (counterpart_lines + writeoff_lines).filtered(lambda line: line.account_id.reconcile)
            amount_residual = sum(reconcile_lines.mapped(residual_field))
            pay.payment_amount_residual = amount_residual

    @api.model
    def create(self, vals):
        res = super(AccountPayment, self).create(vals)
        if self.env.context.get('sarya_reconcile_summary'):
            sarya_reconcile_summary_id = self.env.context.get('sarya_reconcile_summary')
            sarya_reconcile_summary = self.env['sarya.reconcile.summary'].browse(sarya_reconcile_summary_id)
            sarya_reconcile_summary.write({'payment_id' : res.id})
        return res
