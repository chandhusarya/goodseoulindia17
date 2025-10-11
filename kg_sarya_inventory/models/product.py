# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.exceptions import UserError


class Product(models.Model):
    _inherit = 'product.template'

    product_tag_ids = fields.Many2many(
        string="Product Tags",
        comodel_name='product.tag',
        help="These tags can be used to search the product by tags.")

    bl_to_container_split = fields.Selection([('by_value', 'By Value of Container'), ('equal', 'Equally split to Container')],
                                             string="Bl to container split method", default='by_value')

    carton_per_pallet = fields.Float("Carton Per Pallet")

    landed_cost_taxes_id = fields.Many2many('account.tax', 'landed_cost_taxes_rel', 'prod_id', 'tax_id',
                                         string='Landed Cost Custom Duty archived', domain=[('type_tax_use', '=', 'purchase')])

    landed_cost_custom_duty_perc = fields.Float("Landed Cost Custom Duty %")

    is_item_to_monitor = fields.Boolean("Is item to monitor")




class ProductProduct(models.Model):
    _inherit = 'product.product'

    # @api.model
    # @api.returns('self')
    # def search(self, domain, offset=0, limit=None, order=None):
    #     context = self.env.context
    #
    #     print("\n\n")
    #     print("==========================")
    #     print("context ==>> ", context)
    #     print("\n\n")
    #
    #
    #
    #     return super(ProductProduct, self).search(domain, offset=offset, limit=limit, order=order)

    @api.model
    def search_new(self, args, offset=0, limit=None, order=None, count=False):
        """added extra filter to args of lot in order to filter zero stock lot"""
        args = args or []
        context = self.env.context
        if context.get('filter_products_in_bl_allowed') or context.get('filter_products_in_bl_selected'):

            filter_products_in_bl_selected = context['filter_products_in_bl_selected'][0][2]
            if filter_products_in_bl_selected:
                purchase_order_ids = filter_products_in_bl_selected
            else:
                purchase_order_ids = context['filter_products_in_bl_allowed'][0][2]
            if purchase_order_ids:
                allowed_prd = []
                purchase_order = self.env['purchase.order'].browse(purchase_order_ids)
                for po in purchase_order:
                    for po_line in po.order_line:
                        if po_line.product_id.id not in allowed_prd:
                            allowed_prd.append(po_line.product_id.id)
                args.append(['id', 'in', allowed_prd])




        return super(ProductProduct, self).search(args, offset=offset, limit=limit, order=order, count=count)

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):

        context = self.env.context

        print("\n\n\nContext ====>> ", context)
        print("\n\n")


        # filter landed cost as per incoterms
        if context.get('filter_incoterm_landed_cost_purchase'):
            purchase_order_ids = context['filter_incoterm_landed_cost_purchase'][0]
            # Browse po to find incoterm
            if purchase_order_ids:
                allowed_landed_costs_prd = []
                purchase_order = self.env['purchase.order'].browse(purchase_order_ids)
                for po in purchase_order:
                    incoterm_id = po.incoterm_id
                    for lc_prd in incoterm_id.allowed_landed_costs:
                        if lc_prd.id not in allowed_landed_costs_prd:
                            allowed_landed_costs_prd.append(lc_prd.id)
                domain.append(['id', 'in', allowed_landed_costs_prd])

        # Filter products form purchase order based on the vendor
        # This is to filter items on purchase order line
        if context.get('filter_products_from_vendor') and context.get('partner_id'):
            partner_id = context.get('partner_id')

            supplierinfo = self.env['product.supplierinfo'].search([('partner_id', '=', partner_id)])
            prds_of_vendor = []
            for each_si in supplierinfo:
                product_ids = supplierinfo.product_tmpl_id.product_variant_ids.ids
                for prd in product_ids:
                    prds_of_vendor.append(prd)
            domain.append(['id', 'in', prds_of_vendor])


        print("\n\ncontext ======>> ", context)

        # Filter Products from Purchase Order in BL
        if context.get('filter_products_in_bl_allowed') or context.get('filter_products_in_bl_selected'):

            print("\n\ncontext['filter_products_in_bl_selected'] =============>> ", context['filter_products_in_bl_selected'])
            filter_products_in_bl_selected = context['filter_products_in_bl_selected']
            if filter_products_in_bl_selected:
                purchase_order_ids = filter_products_in_bl_selected
            else:
                purchase_order_ids = context['filter_products_in_bl_allowed']

            print("filter_products_in_bl_allowed ==>> ", context.get('filter_products_in_bl_allowed'))
            print("filter_products_in_bl_selected ==>> ", context.get('filter_products_in_bl_selected'))

            if purchase_order_ids:
                allowed_prd = []
                purchase_order = self.env['purchase.order'].browse(purchase_order_ids)
                for po in purchase_order:
                    for po_line in po.order_line:
                        if po_line.product_id.id not in allowed_prd:
                            allowed_prd.append(po_line.product_id.id)
                domain.append(['id', 'in', allowed_prd])

        if 'filter_custom_duty_of_product' in context:
            allowed_prd = []
            container_id = context.get('filter_custom_duty_of_product', False)
            if container_id:
                bl_entry_lines = self.env['bl.entry.lines'].search([('container_id', '=', container_id)])
                for line in bl_entry_lines:
                    if line.product_id:
                        allowed_prd.append(line.product_id.id)
            domain.append(['id', 'in', allowed_prd])

        return super(ProductProduct, self)._name_search(name, domain=domain, operator=operator, limit=limit, order=order)


    @api.model
    def _name_search_new(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        context = self.env.context
        #filter landed cost as per incoterms
        if context.get('filter_incoterm_landed_cost_purchase'):
            purchase_order_ids = context['filter_incoterm_landed_cost_purchase'][0][2]
            #Browse po to find incoterm
            if purchase_order_ids:
                allowed_landed_costs_prd = []
                purchase_order = self.env['purchase.order'].browse(purchase_order_ids)
                for po in purchase_order:
                    incoterm_id = po.incoterm_id
                    for lc_prd in incoterm_id.allowed_landed_costs:
                        if lc_prd.id not in allowed_landed_costs_prd:
                            allowed_landed_costs_prd.append(lc_prd.id)
                args.append(['id', 'in', allowed_landed_costs_prd])

        #Filter products form purchase order based on the vendor
        #This is to filter items on purchase order line
        if context.get('filter_products_from_vendor') and context.get('partner_id'):
            partner_id = context.get('partner_id')

            supplierinfo = self.env['product.supplierinfo'].search([('partner_id', '=', partner_id)])
            prds_of_vendor = []
            for each_si in supplierinfo:
                product_ids = supplierinfo.product_tmpl_id.product_variant_ids.ids
                for prd in product_ids:
                    prds_of_vendor.append(prd)
            args.append(['id', 'in', prds_of_vendor])



         #Filter Products from Purchase Order in BL
        if context.get('filter_products_in_bl_allowed') or context.get('filter_products_in_bl_selected'):

            filter_products_in_bl_selected = context['filter_products_in_bl_selected'][0][2]
            if filter_products_in_bl_selected:
                purchase_order_ids = filter_products_in_bl_selected
            else:
                purchase_order_ids = context['filter_products_in_bl_allowed'][0][2]


            print("filter_products_in_bl_allowed ==>> ", context.get('filter_products_in_bl_allowed'))
            print("filter_products_in_bl_selected ==>> ", context.get('filter_products_in_bl_selected'))



            if purchase_order_ids:
                allowed_prd = []
                purchase_order = self.env['purchase.order'].browse(purchase_order_ids)
                for po in purchase_order:
                    for po_line in po.order_line:
                        if po_line.product_id.id not in allowed_prd:
                            allowed_prd.append(po_line.product_id.id)
                args.append(['id', 'in', allowed_prd])

        return super(ProductProduct, self)._name_search(name, args, operator, limit, name_get_uid)

    def name_get_with_package(self, package_id):
        """
        By default Odoo shows product code + product name in SO, PO and invoice.
        we keep everything same but changes the product name to product package name.
        """
        def _name_get_with_package(d):
            name = d.get('name', '')
            code = self._context.get('display_default_code', True) and d.get('default_code', False) or False
            if code:
                name = '[%s] %s' % (code, name)
            return (d['id'], name)

        partner_id = self._context.get('partner_id')
        if partner_id:
            partner_ids = [partner_id, self.env['res.partner'].browse(partner_id).commercial_partner_id.id]
        else:
            partner_ids = []
        company_id = self.env.context.get('company_id')

        # all user don't have access to seller and partner
        # check access and use superuser
        self.check_access_rights("read")
        self.check_access_rule("read")

        result = []

        # Prefetch the fields used by the `name_get`, so `browse` doesn't fetch other fields
        # Use `load=False` to not call `name_get` for the `product_tmpl_id`
        self.sudo().read(['name', 'default_code', 'product_tmpl_id'], load=False)

        product_template_ids = self.sudo().mapped('product_tmpl_id').ids

        if partner_ids:
            supplier_info = self.env['product.supplierinfo'].sudo().search([
                ('product_tmpl_id', 'in', product_template_ids),
                ('partner_id', 'in', partner_ids),
            ])
            supplier_info.sudo().read(['product_tmpl_id', 'product_id', 'product_name', 'product_code'], load=False)
            supplier_info_by_template = {}
            for r in supplier_info:
                supplier_info_by_template.setdefault(r.product_tmpl_id, []).append(r)
        for product in self.sudo():
            variant = product.product_template_attribute_value_ids._get_combination_name()

            name = variant and "%s (%s)" % (package_id.name, variant) or package_id.name
            sellers = []
            if partner_ids:
                product_supplier_info = supplier_info_by_template.get(product.product_tmpl_id, [])
                sellers = [x for x in product_supplier_info if x.product_id and x.product_id == product]
                if not sellers:
                    sellers = [x for x in product_supplier_info if not x.product_id]
                # Filter out sellers based on the company. This is done afterwards for a better
                # code readability. At this point, only a few sellers should remain, so it should
                # not be a performance issue.
                if company_id:
                    sellers = [x for x in sellers if x.company_id.id in [company_id, False]]
            if sellers:
                for s in sellers:
                    seller_variant = s.product_name and (
                            variant and "%s (%s)" % (s.product_name, variant) or s.product_name
                    ) or False
                    mydict = {
                        'id': product.id,
                        'name': seller_variant or name,
                        'default_code': s.product_code or product.default_code,
                    }
                    temp = _name_get_with_package(mydict)
                    if temp not in result:
                        result.append(temp)
            else:
                mydict = {
                    'id': product.id,
                    'name': name,
                    'default_code': product.default_code,
                }
                result.append(_name_get_with_package(mydict))
        return result


class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    package_id = fields.Many2one('product.packaging', 'Package', check_company=True, copy=False)
    package_price = fields.Float(
        'Price', default=0.0, digits='Product Price',
        required=False, help="The package price to purchase a product")

    @api.model
    def create(self, vals):
        if not self.env.user.has_group('kg_sarya_inventory.can_change_vendor_price_list_master'):
            raise UserError(_('You cannot Add or Edit Purchase price'))
        res = super(SupplierInfo, self).create(vals)
        return res

    def write(self, values):
        if not self.env.user.has_group('kg_sarya_inventory.can_change_vendor_price_list_master'):
            raise UserError(_('You cannot Add or Edit Purchase price'))

        old_price = self.package_price

        res = super(SupplierInfo, self).write(values)

        if 'package_price' in values:
            new_price = values['package_price']
            if new_price != old_price:
                product = self.product_tmpl_id
                msg = "Supplier Price List master update, " \
                      "<br/>Supplier: %s" \
                      "<br/>Packaging: %s" \
                      "<br/>Currency: %s" \
                      "<br/>Price Change: %s -> %s" %(self.partner_id.name, self.package_id.name, self.currency_id.name,
                                                      str(old_price), str(new_price))
                product.message_post(body=msg)
        return res

class ProductTag(models.Model):
    _name = 'product.tag'
    _description = 'Product Tag'

    name = fields.Char('Tag Name', required=True)
    active = fields.Boolean(default=True, help="Set active to false to hide the Product Tag without removing it.")
