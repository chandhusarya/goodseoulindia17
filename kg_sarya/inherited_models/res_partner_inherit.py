# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
# from datetime import datetime, date
from datetime import datetime, timedelta
from dateutil import relativedelta

class Purchase_port_of_discharge(models.Model):
    _name = 'purchase.port.of.discharge'

    name = fields.Char("Place")

    # @api.model
    # def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
    #
    #     context = self.env.context
    #
    #     print("\n\n\n\n---------------------------------------")
    #     print("+++++++++++++++++++++++++++++++++++++++++++++++")
    #     print("context ==>> ", context)
    #     print("\n\n\n\n")
    #
    #     res = super(Purchase_port_of_discharge, self)._name_search(name, args, operator, limit, name_get_uid)
    #     return res

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):

        context = self.env.context

        print("\n\n\n\n=================================")
        print("***********************************************")
        print("context ==>> ", context)
        print("\n\n\n\n")


        if 'filter_port_of_loading' in context:

            clearing_agent = context.get('clearing_agent', False)

            #if not clearing_agent:
            #    domain.append(('name', 'ilike', 'dddfff'))
            if clearing_agent:
                estimation = self.env['fright.charge.estimation'].search([('vendor_id', '=', clearing_agent)])

                port_ids = []
                for port in estimation:
                    port_ids.append(port.from_port.id)

                if port_ids:
                    domain.append(('id', 'in', port_ids))
                else:
                    domain.append(('name', 'ilike', 'dddfff'))


        if 'filter_port_of_discharge' in context:

            clearing_agent = context.get('clearing_agent', False)
            port_of_loading = context.get('port_of_loading', False)

            #f not clearing_agent or not port_of_loading:
            #    domain.append(('name', 'ilike', 'dddfff'))
            if clearing_agent and port_of_loading:
                estimation = self.env['fright.charge.estimation'].search([('vendor_id', '=', clearing_agent),
                                                                         ('from_port', '=', port_of_loading)])
                port_ids = []
                for port in estimation:
                    port_ids.append(port.to_port.id)

                if port_ids:
                    domain.append(('id', 'in', port_ids))
                else:
                    domain.append(('name', 'ilike', 'dddfff'))

        print("_search domain ==>> ", domain)

        res = super(Purchase_port_of_discharge, self)._search(domain, offset=offset,
                                                           limit=limit, order=order,
                                                           access_rights_uid=access_rights_uid)

        return res



class FrightChargeEstimation(models.Model):

    _name = 'fright.charge.estimation'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    vendor_id = fields.Many2one('res.partner', string="Vendor", tracking=True)
    from_port = fields.Many2one('purchase.port.of.discharge', string="From", tracking=True)
    to_port = fields.Many2one('purchase.port.of.discharge', string="To", tracking=True)
    fright_charge = fields.Float("Fright Charge (SAR)", tracking=True)
    container_cost = fields.Float("Custom Duty Container Cost(SAR)", tracking=True)
    price_variance_allowed = fields.Float("Maximum Price Variance allowed")




class PartnerContract(models.Model):
    _name = 'partner.contract'
    _description = 'Partner Contract'

    name = fields.Char()
    date_start = fields.Date('Start Date')
    date_end = fields.Date('End Date')


class CustomerCategory(models.Model):
    _name = 'customer.category'
    _description = 'Customer Category'
    name = fields.Char()
    code = fields.Char()


class CustomerTradeChannel(models.Model):
    _name = 'trade.channel'
    _description = 'Trade Channel'
    name = fields.Char()
    journal = fields.Many2one('account.journal')


class CustomerClass(models.Model):
    _name = 'customer.classification'
    _description = 'Customer Classification'

    name = fields.Char()
    trade_channel_id = fields.Many2one('trade.channel')


class CustomerSubClass(models.Model):
    _name = 'customer.sub.classification'
    _description = 'Customer Sub Class'

    name = fields.Char()
    trade_channel_id = fields.Many2one('trade.channel', string="Trade Channel")
    classification_id = fields.Many2one('customer.classification', string="Classification")
    picking_type_id = fields.Many2one('stock.picking.type', string="Picking Type")


class CustomerSubClass2(models.Model):
    _name = 'customer.sub.classification2'
    _description = 'Customer Sub Class 2'

    name = fields.Char()
    trade_channel_id = fields.Many2one('trade.channel', string="Trade Channel")
    classification_id = fields.Many2one('customer.classification', string="Classification")
    sub_classification_id = fields.Many2one('customer.sub.classification', string="Sub Classification")


class CustomerSubClass3(models.Model):
    _name = 'customer.sub.classification3'
    _description = 'Customer Sub Class 3'

    name = fields.Char()
    trade_channel_id = fields.Many2one('trade.channel', string="Trade Channel")
    classification_id = fields.Many2one('customer.classification', string="Classification")
    sub_classification_id = fields.Many2one('customer.sub.classification', string="Sub Classification")
    sub_classification2_id = fields.Many2one('customer.sub.classification2', string="Sub Classification2")
    picking_type_id = fields.Many2one('stock.picking.type', string="Picking Type")


class SupplierShippingDocument(models.Model):
    _name = 'supplier.shipping.document'

    vendor_id = fields.Many2one('res.partner', string="Vendor")
    name = fields.Char("Document Name")
    is_required = fields.Boolean("Is Mandatory Document?")

    @api.model
    def create(self, vals):
        res = super(SupplierShippingDocument, self).create(vals)
        for doc in res:
            if doc.vendor_id:
                msg = "Shipping document added %s, Is required : %s" % (doc.name, str(doc.is_required))

                print("doc ==>> ", doc)
                print("doc.vendor_id ==>> ", doc.vendor_id)

                doc.vendor_id.message_post(body=msg)
        return res

    def write(self, values):
        res = super(SupplierShippingDocument, self).write(values)
        for doc in self:
            msg = "Shipping document edited. %s" % str(values)
            doc.vendor_id.message_post(body=msg)
        return res

    def unlink(self):
        for doc in self:
            msg = "Shipping document Deleted. %s" % doc.name
            doc.vendor_id.message_post(body=msg)
        return super(SupplierShippingDocument, self).unlink()


class CustomerSubClass4(models.Model):
    _name = 'customer.sub.classification4'
    _description = 'Customer Sub Class 4'

    name = fields.Char()
    trade_channel_id = fields.Many2one('trade.channel', string="Trade Channel")
    classification_id = fields.Many2one('customer.classification', string="Classification")
    sub_classification_id = fields.Many2one('customer.sub.classification', string="Sub Classification")
    sub_classification2_id = fields.Many2one('customer.sub.classification2', string="Sub Classification2")
    sub_classification3_id = fields.Many2one('customer.sub.classification3', string="Sub Classification3")


class ResPartner(models.Model):
    _inherit = 'res.partner'

    parent_customer_id = fields.Many2one('res.partner', string='Parent Customer')
    child_customer_count = fields.Integer(compute='_compute_child_customer_count', string="Child Customers")
    attachment = fields.One2many('partner.attachments', 'partner_id')
    trade_license = fields.Char('Trade License')

    bill_type = fields.Selection([('bill_to_bill', 'Bill To Bill'), ('cash', 'Cash'), ('credit', 'Credit')])
    is_parent = fields.Boolean(default=False, string="Is Parent")
    region = fields.Many2one('customer.region', string='Region')
    subregion = fields.Many2one('region.subregion', string='Sub Region', domain="[('region', '=', region)]")
    contracts = fields.Many2one('partner.contract', string='Contract')
    child_credit_limit = fields.Float('Credit Limit')
    child_credit_total = fields.Float('Child Credit Total', )
    salesman_history = fields.One2many('salesman.history.line', 'partner_id', string='Salesman History')
    acc_mnger_history = fields.One2many('manager.history.line', 'partner_id', string='Ac.Manager History')
    executive_history = fields.One2many('executive.history.line', 'partner_id', string='Executive History')
    user_id = fields.Many2one('res.users', string="Sales Person", compute='_compute_current_customer')
    is_vendor = fields.Boolean(default=False)

    trade_channel = fields.Many2one('trade.channel', string="Trade Channel")
    customer_classification = fields.Many2one('customer.classification', string="Customer Classification")
    customer_sub_classification = fields.Many2one('customer.sub.classification', string="Customer Sub Classification")
    customer_sub_classification2 = fields.Many2one('customer.sub.classification2', string="Customer Sub Classification2")

    customer_sub_classification3 = fields.Many2one('customer.sub.classification3', string="Customer Sub Classification3")

    customer_category_id = fields.Many2one('customer.category')

    show_lot_exp = fields.Boolean(default=False)
    vendor_type = fields.Selection([('trade', 'Trade'),
                                    ('non_trade', 'Non Trade')], string="Vendor Type")
    arabic_name = fields.Char("Arabic Name")
    customer_cr = fields.Char("CR")
    vendor_origin = fields.Selection([('local_vendor', 'Local Vendor'),
                                      ('import_vendor', 'Import Vendor')], string="Local/Import Vendor")

    is_control_list_mandatory = fields.Boolean("Control List Mandatory for POD?")

    port_of_loading = fields.Many2one('purchase.port.of.discharge', string="Port Of Loading")
    shipping_documents = fields.One2many('supplier.shipping.document', 'vendor_id', string="Shipping Documents")
    vendor_mail_template = fields.Many2one('mail.template', string="Document Request E-mail format")

    vendor_po_mail_template = fields.Many2one('mail.template', string="PO e-mail format")

    vendor_bo_mail_template = fields.Many2one('mail.template', string="BO e-mail format")

    is_clearing_agent = fields.Boolean("Is Clearing Agent")
    clearing_agents = fields.Many2many('res.partner', 'partner_clearing_agent_rel', 'id', 'agent_id',
                                       string='Clearing Agents')

    do_mandatory_procurement_approval_required = fields.Boolean("Do procurement approval Required?")

    mode_of_shipment = fields.Selection([('by_sea', 'By Sea'),
                                         ('by_air', 'By Air'),
                                         ('by_road', 'By Road')],
                                        string="Mode of Shipment")

    container_type = fields.Selection(string='Container Type',
                                      selection=[('reefer_chilled', 'Reefer Chilled'),
                                                 ('reefer_frozen', 'Reefer Frozen'),
                                                 ('dry', 'Dry'), ('air', 'Air')], copy=False)

    container_volume = fields.Selection(string='Container Volume',
                                        selection=[('40_feet', '40 Feet'), ('20_feet', '20 Feet'), ('dry', 'Other')],
                                        copy=False)


    def get_invoice_journal(self):
        if self.trade_channel:
            if self.trade_channel.journal:
                return self.trade_channel.journal
            else:
                raise ValidationError('Journal is not configure in the trade channel %s' % self.trade_channel.name)
        else:
            raise ValidationError('Trade channel is not configure on the customer master')



    @api.depends('rental_ids.rent')
    def get_line_rental_total(self):
        total = 0.0
        self.rental_total = 0.0
        for rec in self.rental_ids:
            total += rec.rent
        self.rental_total = total

    #@api.depends('country_id')
    #@api.depends_context('company')
    #def _compute_product_pricelist(self):
    #    company = self.env.company.id
    #    res = self.env['product.pricelist']._get_partner_pricelist_multi(self.ids, company_id=company)
    #    for p in self:
    #        if p.supplier_rank == 0:
    #            p.property_product_pricelist = res.get(p.id)
    #        else:
    #            p.property_product_pricelist = False

    @api.model
    def default_get(self, fields):
        res = super(ResPartner, self).default_get(fields)
        if not self.is_vendor:
            document_lines = [(5, 0, 0),
                              (0, 0, {'document_name': 'Contract Copy'}),
                              (0, 0, {'document_name': 'Vat Registration'}),
                              (0, 0, {'document_name': 'Trade License'}),
                              (0, 0, {'document_name': 'Owners passport / EID'})
                              ]
            res.update({'attachment': document_lines})
        return res

    # contact
    @api.constrains('attachment')
    def _check_attachment_dtls(self):
        if not self.is_vendor:
            if self.is_parent == True or len(self.parent_customer_id) != 0:
                print(self.is_parent)
                print(self.parent_customer_id)
                if (len(self.attachment) < 4):
                    raise ValidationError('Some Attachments are missing')
                for attach in self.attachment:
                    if len(attach.doc_attachment_partner) == 0 and not attach.override_doc:
                        raise ValidationError(_('Attachments missing for %s') % attach.document_name)

    @api.constrains('state_id')
    def _check_state(self):
        if not self.state_id:
            raise ValidationError('Value required for state')

    @api.onchange('trade_channel')
    def onchange_classification(self):
        if self.trade_channel:
            self.customer_classification = False
            self.customer_sub_classification = False
            self.customer_sub_classification2 = False

    @api.onchange('customer_classification')
    def onchange_trade(self):
        if self.customer_classification:
            self.customer_sub_classification = False
            self.customer_sub_classification2 = False

    @api.onchange('customer_sub_classification')
    def onchange_sub_classification(self):
        if self.customer_sub_classification:
            self.customer_sub_classification2 = False

    @api.depends('salesman_history')
    def _compute_current_customer(self):
        self.user_id = self.env.user
        for line in self.salesman_history:
            if line.end_date == False:
                self.user_id = line.salesman.id


    @api.onchange('trade_license', 'vat')
    def _check_vat_trade_license(self):
        if self.trade_license:
            res_partner_trade = self.env['res.partner'].search([('trade_license', '=', self.trade_license)])
            if res_partner_trade:
                raise ValidationError("Exists ! Already a customer exists in this Trade License")

    @api.onchange('is_parent')
    def _onchange_is_parent(self):
        if self.is_parent:
            self.parent_customer_id = False
            self.vat = False
            self.country_id = False

    @api.onchange('parent_customer_id')
    def _onchange_parent_customer_id(self):
        if self.parent_customer_id:
            if self.is_parent:
                raise ValidationError("This is already a Parent Company...")
            self.vat = self.parent_customer_id.vat

    # for each in self:
    #     if len(each.parent_customer_id) != 0:
    #         if each.parent_customer_id.user_id != each.user_id:
    #             raise ValidationError("Salesperson of current customer should be same parent customer's salesperson...")

    # @api.onchange('country_id')
    # def _onchange_country_id(self):
    #     for each in self:
    #         if len(each.parent_customer_id) != 0:
    #             if each.parent_customer_id.country_id != each.country_id:
    #                 raise ValidationError("Region of current customer should be same parent customer's region...")

    @api.onchange('parent_customer_id')
    def _onchange_parent_customer_id(self):
        for each in self:
            if len(each.parent_customer_id) != 0:
                # each.user_id = each.parent_customer_id.user_id.id
                each.country_id = each.parent_customer_id.country_id.id
                each.vat = each.parent_customer_id.vat

    def _compute_child_customer_count(self):
        for partner in self:
            child_customer_count = self.env['res.partner'].search_count([('parent_customer_id', '=', partner.id)])
            partner.child_customer_count = child_customer_count

    def action_get_child_customers(self):
        action = self.env.ref('account.res_partner_action_customer').read()[0]
        action['context'] = {
            'default_parent_customer_id': self.id,
        }
        action['domain'] = [('parent_customer_id', '=', self.id)]
        child_customers = self.env['res.partner'].search([('parent_customer_id', '=', self.id)])
        if self.child_customer_count == 1:
            action['views'] = [(self.env.ref('base.view_partner_form').id, 'form')]
            action['res_id'] = child_customers.id
        return action



    def _get_name(self):
        """ overrided to include customer code """
        partner = self
        name = partner.name or ''
        if partner.cust_sequence:
            name = "%s ‒ %s" % (name, partner.cust_sequence)

        if partner.company_name or partner.parent_id:
            if not name and partner.type in ['invoice', 'delivery', 'other']:
                name = dict(self.fields_get(['type'])['type']['selection'])[partner.type]
            if not partner.is_company:
                name = self._get_contact_name(partner, name)
        if self._context.get('show_address_only'):
            name = partner._display_address(without_company=True)
        if self._context.get('show_address'):
            name = name + "\n" + partner._display_address(without_company=True)
        name = name.replace('\n\n', '\n')
        name = name.replace('\n\n', '\n')
        if self._context.get('partner_show_db_id'):
            name = "%s (%s)" % (name, partner.id)
        if self._context.get('address_inline'):
            splitted_names = name.split("\n")
            name = ", ".join([n for n in splitted_names if n.strip()])
        if self._context.get('show_email') and partner.email:
            name = "%s <%s>" % (name, partner.email)
        if self._context.get('html_format'):
            name = name.replace('\n', '<br/>')
        if self._context.get('show_vat') and partner.vat:
            name = "%s ‒ %s" % (name, partner.vat)
        return name


class Region(models.Model):
    _name = 'customer.region'
    _description = 'Customer Region'

    name = fields.Char()
    code = fields.Char()
    subregion_lines = fields.One2many('region.subregion', 'region', 'Subregions')


class SubRegion(models.Model):
    _name = 'region.subregion'
    _description = 'Region Subregion'

    name = fields.Char()
    code = fields.Char()
    region = fields.Many2one('customer.region', string='Region')


class SalesmanHistoryLines(models.Model):
    _name = 'salesman.history.line'
    _description = 'Salesman History'

    salesman = fields.Many2one('res.users')
    start_date = fields.Date()
    end_date = fields.Date()
    partner_id = fields.Many2one('res.partner')


class ExicutiveHistoryLines(models.Model):
    _name = 'executive.history.line'
    _description = 'Executive History'

    exicutive = fields.Many2one('res.users')
    start_date = fields.Date()
    end_date = fields.Date()
    partner_id = fields.Many2one('res.partner')


class MangerHistoryLines(models.Model):
    _name = 'manager.history.line'
    _description = 'Manager History'

    manager = fields.Many2one('res.users')
    start_date = fields.Date()
    end_date = fields.Date()
    partner_id = fields.Many2one('res.partner')


class PartnerAttachments(models.Model):
    _name = 'partner.attachments'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = 'Attach Documents Related to the Partner'

    document_name = fields.Char("Document Name")
    expiry = fields.Date("Expiry")
    doc_attachment_partner = fields.Many2many('ir.attachment', 'doc_attach_paerner_rel', 'doc_id1', 'attach_id1',
                                              string=" Attachment",
                                              help='You can attach documents', copy=False)
    partner_id = fields.Many2one('res.partner', "Partner")
    product_id = fields.Many2one('product.template', string='Product')
    override_doc = fields.Boolean('Override', default=False, tracking=True,
                                  help="If set yes, creates partner even if attachments are not added")

    is_required = fields.Boolean("Is Mandatory Document?")



    def create(self, vals):
        res = super(PartnerAttachments, self).create(vals)
        for rec in res:
            msg = "Document '%s': override --> %s " % (rec.document_name, rec.override_doc)
            if rec.partner_id:
                rec.partner_id.message_post(body=msg)
            if rec.product_id:
                rec.product_id.message_post(body=msg)
            # fix attachment ownership
            if rec.doc_attachment_partner:
                rec.doc_attachment_partner.sudo().write({'res_model': self._name, 'res_id': rec.id})
        return res

    def write(self, vals):
        for rec in self:
            msg = "Document '%s': override --> %s " % (rec.document_name, rec.override_doc)
            if rec.partner_id:
                rec.partner_id.message_post(body=msg)
            if rec.product_id:
                rec.product_id.message_post(body=msg)
        res = super(PartnerAttachments, self).write(vals)
        return res


class PartnerIrAttachment(models.Model):
    _inherit = 'ir.attachment'

    doc_attach_paerner_rel = fields.Many2many('partner.attachments', 'doc_attachment_partner', 'attach_id1', 'doc_id1',
                                              string="Attachment", invisible=1)

