# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class RebateMaster(models.Model):
    _name = "rebate.master"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _compute_company_id(self):
        self.company_id = self.env.company.id
        self.currency_id = self.company_id.currency_id.id

    name = fields.Char()
    code = fields.Char()
    product_type = fields.Selection([('all_product', 'All Product'), ('selected', 'Selected Product')],
                                    default='all_product')
    customer_section_id = fields.Many2one('customer.section')
    customer_section_ids = fields.Many2many('customer.section')
    brand_id = fields.Many2many('product.manufacturer')
    contract_type = fields.Selection([('customer', 'Customer'), ('sarya', 'Sarya')])
    date_start = fields.Date('Start Date', required=True, help="Starting datetime for the rebatelist item validation\n"
                                                               "The displayed value depends on the timezone set in your preferences.")
    date_end = fields.Date('End Date', required=True, help="Ending datetime for the rebatelist item validation\n"
                                                           "The displayed value depends on the timezone set in your preferences.")
    company_id = fields.Many2one('res.company', compute='_compute_company_id')
    currency_id = fields.Many2one('res.currency')
    fixed_ids = fields.One2many('rebate.fixed.item', 'rebate_id', 'Fixed Rebate', copy=True)
    progressive_ids = fields.One2many('rebate.progressive.item', 'rebate_id', 'Progressive Rebate', copy=True)
    other_ids = fields.One2many('rebate.other.item', 'rebate_id', 'Other Charges', copy=True)
    prevous_amount = fields.Float()
    total_without_progressive = fields.Float(compute='get_total_without_percentage')
    total_with_progressive = fields.Float(compute='get_total_with_percentage')
    status = fields.Boolean(default=False)
    account_move_ids = fields.One2many('account.move', 'rebate_master_id')

    is_rebate_computed_on_untaxed = fields.Boolean("Is Rebate computed on untaxed?")

    rebate_customer_for_posting = fields.Many2one('res.partner', string='Rebate Customer for posting')

    def rebate_journal_view(self):
        self.ensure_one()
        domain = [
            ('rebate_master_id', '=', self.id)]
        return {
            'name': _('Journal Entries'),
            'domain': domain,
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
        }

    @api.onchange('prevous_amount')
    def _onchange_previous_amount(self):
        if self.progressive_ids:
            self.write({'progressive_ids': [(5, 0, 0)]})

    @api.depends('fixed_ids.percentage')
    def get_total_without_percentage(self):
        """Compute total rebate without progressive"""
        for rec in self:
            total_without_progressive = 0
            for line in rec.fixed_ids:
                if line.rebate_active:
                    total_without_progressive += line.percentage
            rec.total_without_progressive = total_without_progressive

    @api.depends('fixed_ids.percentage', 'progressive_ids.rebate_percentage')
    def get_total_with_percentage(self):
        """Compute total rebate with progressive"""
        for rebate in self:
            rebate.total_with_progressive = 0.00
            for line in rebate.fixed_ids:
                if line.rebate_active:
                    rebate.total_with_progressive = rebate.total_with_progressive + line.percentage
            rebate_percent = 0.00
            for line in rebate.progressive_ids:
                if line.rebate_active:
                    if rebate_percent < line.rebate_percentage:
                        rebate_percent = line.rebate_percentage
            rebate.total_with_progressive = rebate.total_with_progressive + rebate_percent

    def create_pricelist(self):
        """Loading wizard for Price list Creation"""
        if self.product_type == 'selected':
            wizard = self.env['pricelist.wizard'].create(
                {'product_type': self.product_type, 'company_id': self.company_id.id,
                 'brand_id': [(6, 0, self.brand_id.ids)], 'customer_section_id': self.customer_section_id.id,
                 'rebate_id': self.id})
            products = self.env['product.template'].search(
                [('brand', 'in', self.brand_id.ids), ('section', '=', self.customer_section_id.id)])
            details_list = []
            for product in products:
                pr_pr_id = self.env['product.product'].search([('product_tmpl_id', '=', product.id)])
                details_list.append((0, 0, {'product_product_id': [(6, 0, pr_pr_id.ids)], 'product_id': product.id}))
            wizard.product_ids = details_list
        else:
            wizard = self.env['pricelist.wizard'].create(
                {'product_type': self.product_type, 'company_id': self.company_id.id, 'rebate_id': self.id})
            products = self.env['product.template'].search([('detailed_type', '=', 'product')])
            details_list = []
            for product in products:
                pr_pr_id = self.env['product.product'].search([('product_tmpl_id', '=', product.id)])
                details_list.append((0, 0, {'product_product_id': [(6, 0, pr_pr_id.ids)], 'product_id': product.id}))
            wizard.product_ids = details_list
        return {
            'name': _('Product List'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('kg_sarya_rebate.pricelist_wizard_form').id,
            'res_model': 'pricelist.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': wizard.id
        }


class FixedRebateLine(models.Model):
    _name = "rebate.fixed.item"
    _rec_name = 'description'

    description = fields.Char()
    account_id = fields.Many2one('account.account', required=True)
    percentage = fields.Float()
    rebate_id = fields.Many2one('rebate.master')
    rebate_active = fields.Boolean("Active", default=True)

    def unlink(self):
        for fixed_item in self:
            move_line = self.env['account.move.line'].search([('rebate_fixed_id', '=', fixed_item.id)])
            if move_line:
                raise UserError(_('Rebate entry is already generated for this line, So you cannot delete this rebate line, Please deactivate'))
        return super().unlink()


class OtherRebateLine(models.Model):
    _name = "rebate.other.item"
    _rec_name = 'description'

    description = fields.Char()
    percentage = fields.Float()
    account_id = fields.Many2one('account.account', string='Account', domain=[('deprecated', '=', False)])
    rebate_id = fields.Many2one('rebate.master')
    partner_id = fields.Many2many('res.partner')
    rebate_active = fields.Boolean("Active", default=True)

    def unlink(self):
        for fixed_item in self:
            move_line = self.env['account.move.line'].search([('rebate_other_id', '=', fixed_item.id)])
            if move_line:
                raise UserError(_('Rebate entry is already generated for this line, So you cannot delete this rebate line, Please deactivate'))
        return super().unlink()


class ProgressiveRebateLine(models.Model):
    _name = "rebate.progressive.item"
    _rec_name = 'name'

    name = fields.Char(compute='_compute_name')
    slab = fields.Char(required=True)
    slab_type = fields.Selection([('percentage', 'Percentage'), ('fixed', 'Value')], default='percentage')
    account_id = fields.Many2one('account.account', required=True, string='Debit Account')
    percentage = fields.Float()
    slab_vale = fields.Float()
    rebate_percentage = fields.Float()
    rebate_id = fields.Many2one('rebate.master')
    target_val = fields.Float('Target')
    current_slab = fields.Boolean('Active slab', default=False)
    rebate_active = fields.Boolean("Active", default=True)

    @api.depends('rebate_id', 'slab', 'rebate_id.name')
    def _compute_name(self):
        for rec in self:
            rec.name = '[%s] %s' % (rec.rebate_id.name, rec.slab)

    @api.onchange('slab_type')
    def _onchange_slab_type(self):
        if self.slab_type == 'percentage':
            self.slab_vale = False
        else:
            self.percentage = False

    @api.onchange('percentage', 'slab_vale')
    def _calculate_target_value(self):
        previous_year_sale = self.rebate_id.prevous_amount
        if previous_year_sale:
            if self.slab_type == 'percentage':
                val = previous_year_sale * (self.percentage / 100)
                self.target_val = previous_year_sale + val
            else:
                self.target_val = previous_year_sale + self.slab_vale
        else:
            raise UserError(_("Enter previous sale's value"))


class PriceListInh(models.Model):
    _inherit = "product.pricelist.item"

    # def _get_default_description(self):

    # 	return date.today().year

    rebate_id = fields.Many2one('rebate.master')
    packging_id = fields.Many2one('product.packaging')
    product_pr_id = fields.Many2one('product.product', copy=True)
    package_desc = fields.Char()
    active = fields.Boolean(
        string='Active', default=True,
        help='If unchecked, it will allow you to hide the pricelist without removing it.')

    @api.onchange('product_tmpl_id')
    def onchange_product_tmpl_id(self):
        if self.product_tmpl_id:
            pr = self.env['product.product'].search([('product_tmpl_id', '=', self.product_tmpl_id.id)])
            for el in pr:
                self.product_pr_id = el.id

    @api.onchange('packging_id')
    def onchange_packging_id(self):
        if self.packging_id:
            self.package_desc = self.packging_id.description

    def action_archive(self):
        for rec in self:
            rec.active = False

    def action_unarchive(self):
        for rec in self:
            rec.active = True
