# -*- coding: utf-8 -*-

from odoo import models, fields, _, api
from odoo.exceptions import ValidationError,UserError
from datetime import date


class PromotionEntry(models.Model):
    _name = 'promotion.entry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Promotion Entry'
    _order = 'name desc, id desc'

    name = fields.Char(string='Reference', required=True, readonly=True, default=lambda self: _('New'), copy=False)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
                                 default=lambda self: self.env.company)
    state = fields.Selection(
        string='Status',
        selection=[
            ('draft', 'Draft'),
            ('open', 'Open'),
            ('done', 'Closed'),
            ('cancel', 'Cancelled'),
        ],
        required=True, tracking=True, default='draft')

    partner_id = fields.Many2one('res.partner', 'Customer', )
    event_name = fields.Char('Event')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    event_type = fields.Many2one('promotion.type', 'Event Type')
    apply_to_all = fields.Boolean('Apply to all child companies', default=False)
    leaflet_fee = fields.Float('Leaflet fee')
    rental = fields.Float('Rental')
    line_ids = fields.One2many('promotion.entry.lines', 'parent_id')
    product_ids = fields.One2many('promotion.product.lines', 'parent_id')
    move_id = fields.Many2one('account.move')

    @api.model
    def create(self, vals):
        if not vals.get('name') or vals['name'] == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('promotion.entry') or _('New')
        return super(PromotionEntry, self).create(vals)

    def action_confirm(self):
        for rec in self:
            rec.write({
                'state': 'done',
            })
            leaflet_account_id = self.env['ir.config_parameter'].sudo().get_param('kg_sarya_inventory.leaflet_fee_account_id') or False
            if not leaflet_account_id:
                raise UserError(_("Please configure leaflet fee account from settings"))
            rental_account_id = self.env['ir.config_parameter'].sudo().get_param('kg_sarya_inventory.rental_fee_account_id') or False
            if not rental_account_id:
                raise UserError(_("Please configure rental fee account from settings"))
            promotion_journal_id = self.env['ir.config_parameter'].sudo().get_param('kg_sarya_inventory.promotion_journal_id') or False
            if not promotion_journal_id:
                raise UserError(_("Please configure promotion journal from settings"))
            if rec.apply_to_all:
                """Journal entry for promotion if applied to all child"""
                move_lines = []                
                a = {}
                a['debit'] = rec.leaflet_fee
                a['partner_id'] = rec.partner_id.id if rec.partner_id.id else False
                a['account_id'] = int(leaflet_account_id)
                a['name'] = 'Leaflet Fee'
                c = (0, 0, a)
                move_lines.append(c)
                b = {}
                b['debit'] = rec.rental
                b['partner_id'] = rec.partner_id.id if rec.partner_id.id else False
                b['account_id'] = int(rental_account_id)
                b['name'] = 'Rental Fee'
                d = (0, 0, b)
                move_lines.append(d)
                e = {}
                e['credit'] = rec.rental+rec.leaflet_fee
                e['partner_id'] = rec.partner_id.id if rec.partner_id.id else False
                e['account_id'] = rec.partner_id.property_account_payable_id.id
                f = (0, 0, e)
                move_lines.append(f)
                move = self.env['account.move'].create(
                                    {'payment_reference': 'Promotion', 'promotion_id': self.id, 'ref': self.name,
                                     'name': '/', 'journal_id': int(promotion_journal_id), 'date': date.today(),
                                     'line_ids': move_lines})
                move.action_post()
                rec.update({'move_id':move.id})
                price_list = rec.partner_id.property_product_pricelist
                for product in rec.product_ids:
                    if not product.price_list_id:
                        vals = {
                            'product_tmpl_id': product.product_id.id,
                            'fixed_price': product.price,
                            'date_start': rec.start_date,
                            'date_end': rec.end_date,
                            'packging_id': product.product_package_id.id,
                            'package_desc':product.product_package_id.description
                        }
                        price_list.write({
                            'item_ids': [(0, 0, vals)]
                        })
                        product.price_list_id = price_list.id

            else:
                """Journal entry for each child"""
                customer_list = []
                for line in rec.line_ids:
                    customer_list.append(line.partner_id.id)
                    move_lines = []                
                    a = {}
                    a['debit'] = line.leaflet_fee
                    a['partner_id'] = line.partner_id.id if line.partner_id.id else False
                    a['account_id'] = int(leaflet_account_id)
                    a['name'] = 'Leaflet Fee'
                    c = (0, 0, a)
                    move_lines.append(c)
                    b = {}
                    b['debit'] = line.rental
                    b['partner_id'] = line.partner_id.id if line.partner_id.id else False
                    b['account_id'] = int(rental_account_id)
                    b['name'] = 'Rental Fee'
                    d = (0, 0, b)
                    move_lines.append(d)
                    e = {}
                    e['credit'] = line.rental+line.leaflet_fee
                    e['partner_id'] = line.partner_id.id if line.partner_id.id else False
                    e['account_id'] = line.partner_id.property_account_payable_id.id
                    f = (0, 0, e)
                    move_lines.append(f)
                    move = self.env['account.move'].create(
                                        {'payment_reference': 'Promotion', 'promotion_line_id': self.id, 'ref': self.name,
                                         'name': '/', 'journal_id': int(promotion_journal_id), 'date': date.today(),
                                         'line_ids': move_lines})
                    move.action_post()
                    line.update({'move_id':move.id})   
                """create a new price list with this child""" 
                matching_price_list = self.env['product.pricelist']
                price_list = self.env['product.pricelist'].search([('customer_ids','in',tuple(customer_list))])
                for elm in price_list:
                    if all(item in elm.customer_ids.ids for item in customer_list):
                        matching_price_list = elm
                        break
                if len(matching_price_list) > 0:
                    new_pricelist = matching_price_list.copy()
                    # new_pricelist = self.env['product.pricelist'].search([('id','=',new_pricelist_id)])
                    new_pricelist.update({'name':'Promotion- '+new_pricelist.name,'start_date':rec.start_date,'end_date':rec.end_date,'customer_ids':customer_list}) 
                    val_list = []
                    for line in rec.product_ids:
                        vals = {
                            'product_tmpl_id': line.product_id.id,
                            'fixed_price': line.price,
                            'date_start': rec.start_date,
                            'date_end': rec.end_date,
                            'packging_id': line.product_package_id.id,
                            'package_desc':line.product_package_id.description
                        }
                        line.price_list_id = matching_price_list.id
                        val_list.append([0,0,vals])
                    new_pricelist.update({'item_ids': val_list})
                    for line in new_pricelist.item_ids:
                        line.update({'date_start': rec.start_date,'date_end': rec.end_date})
                    matching_price_list.write({
                        'item_ids': val_list
                    })            
                else:
                     raise ValidationError(_('There no matching pricelist found'))

    def action_cancel(self):
        for rec in self:
            rec.write({
                'state': 'cancel',
            })

    def action_reset(self):
        for rec in self:
            rec.write({
                'state': 'draft',
            })


class PromotionEntryLines(models.Model):
    _name = 'promotion.entry.lines'
    _description = 'Promotion Entry Lines'
    _order = 'id desc'

    parent_id = fields.Many2one('promotion.entry')
    partner_id = fields.Many2one('res.partner', 'Child Customer')
    leaflet_fee = fields.Float('Leaflet fee')
    rental = fields.Float('Rental')
    move_id = fields.Many2one('account.move')


class PromotionEntryProducts(models.Model):
    _name = 'promotion.product.lines'
    _description = 'Promotion Product Lines'
    _order = 'id desc'

    parent_id = fields.Many2one('promotion.entry')
    product_id = fields.Many2one('product.template', 'Product')
    product_pr_id = fields.Many2one('product.product', 'Product')
    product_package_id = fields.Many2one('product.packaging')
    price = fields.Float('Price')
    price_list_id = fields.Many2one('product.pricelist')

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            pr = self.env['product.product'].search([('product_tmpl_id', '=', self.product_id.id)])
            for el in pr:
                self.product_pr_id = el.id


class PromotionType(models.Model):
    _name = 'promotion.type'
    _description = 'Promotion Type'
    _order = 'name desc, id desc'

    name = fields.Char(string='Reference', required=True, readonly=True, default=lambda self: _('New'), copy=False)
