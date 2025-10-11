# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CustomerSection(models.Model):
    _name = 'customer.section'
    _description = 'Customer Section for Product Item'

    name = fields.Char('Customer Section')
    code = fields.Char('Code')


class ProductReference(models.Model):
    _name = 'product.reference'
    _description = 'Product Reference'

    name = fields.Char('Product Reference')
    code = fields.Char('Code', size=1)


class NewItemCode(models.Model):
    _name = 'item.code'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Create new Item code'
    _rec_name = 'product_name'

    product_name = fields.Char()
    description = fields.Text()
    catelog_number = fields.Char()
    search_text = fields.Char()
    stock_type = fields.Selection([('product', 'STOCK'), ('consu', 'NON STOCK')], default='product')
    shelf_life = fields.Integer()
    # best_bfr_sell = fields.Integer()
    best_before_sell = fields.Float()
    primary_uom = fields.Many2one('uom.uom')
    uom_category = fields.Many2one('uom.category')

    @api.onchange('primary_uom')
    def onchange_primary_uom(self):
        for rec in self:
            if rec.primary_uom:
                rec.uom_category = rec.primary_uom.category_id.id

    sale_uom = fields.Many2one('uom.uom')
    purchase_uom = fields.Many2one('uom.uom')
    category = fields.Many2one('product.category')
    brand = fields.Many2one('product.manufacturer')
    section = fields.Many2one('customer.section')
    internal_reference = fields.Many2one('product.reference')
    internal_reference_code = fields.Char(size=1)
    category_type = fields.Selection([('food', 'FOOD'), ('non food', 'NON FOOD')], default='food')
    category_area = fields.Selection([('local', 'LOCAL'), ('foreign', 'FOREIGN')], default='local')
    req_date = fields.Date(default=fields.Datetime.now)
    req_user = fields.Many2one('res.users', default=lambda self: self.env.user)
    aprv_user = fields.Many2one('res.users', default=lambda self: self.env.user)
    item_code = fields.Char(readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm')])

    internal_ref = fields.Char(string='Product Reference')

    @api.onchange('internal_reference')
    def onchange_internal_reference(self):
        for rec in self:
            if rec.internal_reference:
                rec.internal_reference_code = rec.internal_reference.code

    def confirm_item(self):
        if self.brand and self.category:
            if not self.category.next_no:
                self.category.next_no = 100
            self.item_code = str(self.category.prefix) + "-" + str(self.brand.code) + "-A-" + str(self.category.next_no)
            self.category.next_no = self.category.next_no + 1
        product_tmpl = self.env['product.template']
        product_tmpl.create({
            'name': self.product_name,
            'display_name': self.product_name,
            'description': self.description,
            'catelog_number': self.catelog_number,
            'search_text': self.search_text,
            'detailed_type': self.stock_type,
            'primary_uom': self.primary_uom.id,
            'uom_id': self.sale_uom.id,
            'uom_po_id': self.purchase_uom.id,
            'categ_id': self.category.id,
            'brand': self.brand.id,
            'section': self.section.id,
            'section_code': self.section.code,
            'category_type': self.category_type,
            'category_area': self.category_area,
            'name': self.product_name,
            'sale_ok': True,
            'purchase_ok': True,
            'create_uid': self.env.user.id,
            'company_id': self.env.company.id,
            'currency_id': self.env.company.currency_id.id,
            # 'default_code': self.item_code,
            'internal_ref': self.internal_ref,
            'product_reference': self.internal_reference.id,
            'product_reference_code': self.internal_reference.code
        })
        self.state = 'confirm'


class ProductCategoryInh(models.Model):
    _inherit = 'product.category'

    prefix = fields.Char(required=False)
    next_no = fields.Integer(readonly=True, default=100)


class Manufacturer(models.Model):
    _name = 'product.manufacturer'
    _description = 'Brand'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    sequence_id = fields.Many2one("ir.sequence", string='Sequence', ondelete='cascade')

    _sql_constraints = [
        ('code_company_uniq', 'unique (code,company_id)', 'The code of the brand must be unique per company !')
    ]

    @api.model
    def create(self, vals):
        res = super(Manufacturer, self).create(vals)
        if not res.sequence_id:
            sequence_vals = {
                'name': 'Brand %s-%s Sequence' % (res.code, res.name),
                'implementation': 'no_gap',
                'code': 'brand.%s' % res.code,
                'padding': 4,
                'company_id': self.env.company.id
            }
            sequence_id = self.env['ir.sequence'].sudo().create(sequence_vals)
            res.sequence_id = sequence_id.id
        return res


class TemplateInh(models.Model):
    _inherit = 'product.template'

    catelog_number = fields.Char()
    search_text = fields.Char()
    shelf_life = fields.Integer()
    best_bfr_sell = fields.Integer()
    best_before_sell = fields.Float()
    primary_uom = fields.Many2one('uom.uom')
    brand = fields.Many2one('product.manufacturer')
    section = fields.Many2one('customer.section', string="Customer Section")
    section_code = fields.Char()

    category_type = fields.Selection([('food', 'FOOD'), ('non food', 'NON FOOD')], default='food')
    category_area = fields.Selection([('local', 'LOCAL'), ('foreign', 'FOREIGN')], default='local')
    product_reference = fields.Many2one('product.reference')
    product_reference_code = fields.Char(size=1)
    internal_ref = fields.Char(size=1, string='REM')
    seller_ids = fields.One2many('product.supplierinfo', 'product_tmpl_id', 'Vendors', depends_context=('company',),
                                 help="Define vendor pricelists.", required=True)

    primary_uom_qty = fields.Float(default=1)

    def write(self, vals):
        res = super(TemplateInh, self).write(vals)
        if 'attribute_line_ids' in vals or (vals.get('active') and len(self.product_variant_ids) == 0):
            self._create_variant_code_ids()
        return res

    #
    # @api.onchange('packaging_ids.primary_unit')
    # def check_primary_unit(self):
    #     for rec in self.packaging_ids:
    #         for each in rec.product_variant_ids:
    #             primary_packaging_id = self.env['product.packaging'].search([('product_id','=',each.product_id),('primary_unit','=',True)])
    #             if len(primary_packaging_id) == 1:
    #                 raise ValidationError('You cannot make 2 packaging simultaneosly as primary')
    #

    @api.onchange('section_code')
    def onchange_section_code(self):
        for rec in self:
            if rec.section_code:
                section = self.env['customer.section'].search([('code', '=', rec.section_code)])
                if len(section) > 0:
                    rec.section = section.id

    @api.onchange('section')
    def onchange_section(self):
        for rec in self:
            if rec.section:
                rec.section_code = rec.section.code

    @api.onchange('product_reference')
    def onchange_product_reference(self):
        for rec in self:
            if rec.product_reference:
                rec.product_reference_code = rec.product_reference.code

    @api.onchange('product_reference_code')
    def onchange_product_reference_code(self):
        for rec in self:
            if rec.product_reference_code:
                pr_ref = self.env['product.reference'].search([('code', '=', rec.product_reference_code)])
                if len(pr_ref) > 0:
                    rec.product_reference = pr_ref.id

    @api.model
    def create(self, vals):
        if vals.get('detailed_type') == 'product':

            #Deactivating mandatory vendor selection during item creation
            if not vals.get('primary_uom') and False:
                if 'seller_ids' in vals:
                    if len(vals.get('seller_ids')) == 0:
                        raise ValidationError('Select at least one Vendor...')
            if 'attachment_ids' in vals:
                if len(vals.get('attachment_ids')) == 0:
                    raise ValidationError('Attachment is required...')
            brand = self.env['product.manufacturer'].browse(vals.get('brand'))
            section = self.env['customer.section'].browse(vals.get('section'))
            next_code = brand.sequence_id.next_by_id()
            code = "%s-%s-%s%s" % (brand.code, section.code, vals.get('product_reference_code', False) or '', next_code)
            vals['default_code'] = code
            res = super(TemplateInh, self).create(vals)
            product = self.env['product.product'].search([('product_tmpl_id', '=', res.id)], limit=1)
            packaging = self.env['product.packaging'].search([('purchase', '=', True), ('product_id', '=', product.id)],
                                                             limit=1)
            for line in res.seller_ids:
                if not line.package_id:
                    line.package_id = packaging.id
        else:
            res = super(TemplateInh, self).create(vals)

        return res

    def _create_variant_code_ids(self):
        for tmpl_id in self:
            all_variants = tmpl_id.with_context(active_test=False).product_variant_ids.sorted(
                lambda p: (p.active, -p.id))
            count = 0
            for variant in all_variants:
                if variant.pr_internal_ref:
                    count = count + 1
            count += 1
            for variant in all_variants:
                if not variant.pr_internal_ref:
                    if variant.pr_internal_ref:
                        variant.pr_internal_ref = variant.product_reference_code + "-" + str(count)
                        count += 1


class ProductInh(models.Model):
    _inherit = 'product.product'

    pr_internal_ref = fields.Char()


class ProductPackagingIng(models.Model):
    _inherit = "product.packaging"

    description = fields.Char()
    current_stock = fields.Float(compute='get_current_stock')
    primary_unit = fields.Boolean(string='Primary Unit')
    short_code = fields.Char(string="Short Code", related='package_type_id.short_code', store=True)

    @api.onchange('primary_unit')
    def set_primary_uom(self):
        if self.primary_unit and self.sales:
            self.product_id.product_tmpl_id.primary_uom_qty = self.qty
        else:
            self.product_id.product_tmpl_id.primary_uom_qty = 1

    @api.onchange('primary_unit')
    @api.constrains('primary_unit')
    def check_primary_unit(self):
        if self.product_id.exists():
            primary_packaging_id = self.env['product.packaging'].search(
                [('product_id', '=', self.product_id.id), ('primary_unit', '=', True)])
            if len(primary_packaging_id) > 1:
                raise ValidationError('You cannot make 2 packaging simultaneosly as primary')

    @api.depends('qty')
    def get_current_stock(self):
        for pack in self:
            pack.current_stock = 0.00
            pack.current_stock = pack.product_id.qty_available / pack.qty

    @api.constrains('barcode')
    def _check_barcode_uniqueness(self):
        """ With GS1 nomenclature, products and packagings use the same pattern. Therefore, we need
        to ensure the uniqueness between products' barcodes and packagings' ones"""
        # domain = [('barcode', 'in', [b for b in self.mapped('barcode') if b])]
        # if self.env['product.product'].search(domain, order="id", limit=1):
        #     raise ValidationError(_("A product already uses the barcode"))
        # Disable barcode check
        pass
