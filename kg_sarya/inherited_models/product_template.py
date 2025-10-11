from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ps_each_barcode = fields.Char("Each Barcode")
    ps_multipack_barcode = fields.Char("Multipack Barcode")
    ps_carton_barcode = fields.Char("Carton Barcode")

    ps_brand_arabic = fields.Char("Brand Arabic")
    ps_ar_desc = fields.Char("Arabic Description")

    ps_hs_code = fields.Char("HS Code")
    ps_origin = fields.Char("Origin")
    ps_shelf_life = fields.Char("Shelf Life", tracking=True)

    ps_primary_uom = fields.Char("Primary UOM")
    ps_carton_uom_box = fields.Char("Carton UOM - BOX")
    ps_pc_box = fields.Char("PC BOX")

    ps_prd_listing_shot_desc_eng = fields.Char("Product Listing - SHORT DESCRIPTION - English")
    ps_prd_listing_shot_desc_ar = fields.Char("Product Listing - SHORT DESCRIPTION - Arabic")

    ps_long_desc_eng_without_brand = fields.Char("Product Listing- Long Description - English - Without Brand")
    ps_long_desc_eng_with_brand = fields.Char("Product Listing- Long Description - English - With Brand")
    ps_long_desc_ar_with_brand = fields.Char("Product Listing- Long Description - Arabic - With Brand")
    ps_long_desc_ar_without_brand = fields.Char("Product Listing- Long Description - Arabic - Without Brand")

    ps_dime_unit_length = fields.Char("Dimension - Unit (CM) - LENGTH")
    ps_dime_unit_width = fields.Char("Dimension - Unit (CM) - WIDTH")
    ps_dime_unit_height = fields.Char("Dimension - Unit (CM) - HEIGHT")
    ps_dime_unit_diameter = fields.Char("Dimension - Unit (CM) - DIAMETER")

    ps_dime_ctn_length = fields.Char("Dimension - Carton (CM) - LENGTH")
    ps_dime_ctn_width = fields.Char("Dimension - Carton (CM) - WIDTH")
    ps_dime_ctn_height = fields.Char("Dimension - Carton (CM) - HEIGHT")

    ps_pallet_length = fields.Char("PALLET SIZE (CM) - LENGTH")
    ps_pallet_width = fields.Char("PALLET SIZE (CM) - WIDTH")
    ps_pallet_height = fields.Char("PALLET SIZE (CM) - HEIGHT")

    ps_ingredients_eng = fields.Char("INGREDIENTS - ENGLISH")
    ps_ingredients_ar = fields.Char("INGREDIENTS - ARABIC")

    ps_nutritional_facts_eng = fields.Char("NUTRITIONAL FACTS - ENGLISH")
    ps_nutritional_facts_ar = fields.Char("NUTRITIONAL FACTS - ARABIC")

    ps_storage_condition = fields.Char("Storage Condition")


    attachment_ids = fields.One2many('partner.attachments', 'product_id', string='Attachments')

    product_attachment_ids = fields.One2many('product.attachments', 'product_id', string='Attachments')

    is_a_custom_duty = fields.Boolean('Is this custom duty?', default=False)
    is_a_freight_charge = fields.Boolean('Is this freight charge?', default=False)

    #By mistake added this field, to be removed
    is_custom_duty = fields.Boolean('Is this custom duty?', default=False)

    manufactured_by = fields.Char(string='Manufactured By', copy=False)
    address = fields.Text(string='Address', copy=False)

    food_category = fields.Selection([
        ('vegetarian', 'Vegetarian'),
        ('non_vegetarian', 'Non-Vegetarian')], string='Food Category')


    @api.model
    def default_get(self, fields_list):
        res = super(ProductTemplate, self).default_get(fields_list)
        document_data = [(5, 0, 0),
                         (0, 0, {'document_name': 'Product Image'}),
                         (0, 0, {'document_name': 'Product Artwork'})
                         ]
        res.update({
            'attachment_ids': document_data
        })
        return res

class ProductAttachments(models.Model):
    _name = 'product.attachments'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = 'Attach Documents Related to the Products'

    document_name = fields.Selection([('product_image', 'Product Image'),
                                       ('product_artwork', 'Product Artwork'),
                                       ('label_assessment', 'Label Assessment'),
                                       ('registration_certificate', 'Registration Certificate')], string="Type", required=True)

    product_attachment = fields.Many2many('ir.attachment', 'product_attachments_ir_attach_rel', 'prd_atta_id', 'ir_atta_id',
                                              string="File",
                                              help='You can attach documents', copy=False, required=True)

    product_id = fields.Many2one('product.template', string='Product')
    override_doc = fields.Boolean('Override', default=False, tracking=True,
                                  help="If set yes, creates partner even if attachments are not added")
    document_type = fields.Many2one('product.attachments.types', string='File')

    @api.model
    def create(self, vals):
        res = super(ProductAttachments, self).create(vals)
        # fix attachment ownership
        for template in res:
            if template.product_attachment:
                template.product_attachment.sudo().write({'res_model': self._name, 'res_id': template.id})
        return res


class ProductAttachmentsLine(models.Model):
    _name = 'product.attachments.types'

    _order = 'document_name desc'

    document_name = fields.Selection([('product_image', 'Product Image'),
                                      ('product_artwork', 'Product Artwork'),
                                      ('label_assessment', 'Label Assessment'),
                                      ('registration_certificate', 'Registration Certificate')], string="Type", required=True)
    name = fields.Char("File")


class ProductPackagingIng(models.Model):
    _inherit = "product.packaging"

    description = fields.Char("Description")
    primary_unit = fields.Boolean(string='Primary Unit')
