# -*- coding: utf-8 -*-

import logging

from odoo import models, fields, _, api
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare

_logger = logging.getLogger(__name__)


class RebateEntry(models.Model):
    _name = "rebate.entry"
    _description = "Rebate Entries"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))
    rebate_id = fields.Many2one('rebate.master', string='Rebate', copy=False)
    date_start = fields.Date(related='rebate_id.date_start', store=True)
    date_end = fields.Date(related='rebate_id.date_end', store=True)
    partner_id = fields.Many2one('res.partner', readonly=True, tracking=True,
                                 check_company=True, required=True,
                                 string='Partner', change_default=True)
    partner_parent_id = fields.Many2one(related='partner_id.parent_id')
    rebate_item_lines = fields.One2many('rebate.item', 'rebate_entry_id', 'Rebate Items')
    fixed_rebate_lines = fields.One2many('rebate.fixed.entry.line', 'parent_id', 'Fixed Rebates')
    fixed_rebate_percentage = fields.Float(string='Fixed Rebate %')
    total_rebate_fixed_amount = fields.Monetary('Fixed Rebate Amount', compute='_compute_total_rebate_fixed_amount',
                                                store=True)
    progressive_rebate_id = fields.Many2one('rebate.progressive.item', 'Prog. Rebate')
    progressive_rebate_percentage = fields.Float(string='Prog. Rebate %', copy=False)
    total_rebate_progressive_amount = fields.Monetary('Prog. Rebate Amount')
    total_rebate_amount = fields.Monetary('Total Rebate Amount', compute='_compute_total_rebate_amount', store=True)
    entry_type = fields.Selection(
        string='Type',
        selection=[('normal', 'Normal'),
                   ('reservation', 'Reservation')],
        required=True, default='normal')
    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id', store=True)
    move_ids = fields.One2many('account.move.line', 'rebate_entry_id', string='Journal Entries', copy=False)

    # we should restrict to create multiple records with same partner_id, rebate and company.
    _sql_constraints = [
        ('rebate_entry_uniq', 'unique (partner_id,rebate_id,company_id,active)',
         'One customer can have only one rebate entry under a rebate!')
    ]

    @api.depends('fixed_rebate_lines.rebate_fixed_amount')
    def _compute_total_rebate_fixed_amount(self):
        for rec in self:
            rec.total_rebate_fixed_amount = sum(rec.fixed_rebate_lines.mapped('rebate_fixed_amount'))

    @api.depends('total_rebate_fixed_amount', 'total_rebate_progressive_amount')
    def _compute_total_rebate_amount(self):
        for rec in self:
            rec.total_rebate_amount = rec.total_rebate_fixed_amount + rec.total_rebate_progressive_amount

    @api.model
    def create(self, vals):
        if 'company_id' in vals:
            self = self.with_company(vals['company_id'])
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            if 'date' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date']))
            vals['name'] = self.env['ir.sequence'].next_by_code('rebate.entry', sequence_date=seq_date) or _('New')
        result = super(RebateEntry, self).create(vals)
        return result

    def copy(self, default=None):
        # restrict user to duplicate a rebate entry as the records have to be created functionally.
        raise UserError(_('Duplicating a rebate entry is not allowed.'))

    def unlink(self):
        if self.move_ids.filtered(lambda l: l.parent_state != 'cancel'):
            raise UserError(_("You cannot delete this record as there are some "
                              "posted journal entries related to this record. "
                              "Please cancel or delete those journal entries first."))
        return super(RebateEntry, self).unlink()

    def _get_rebate_partner(self, partner_id):
        """We consider only parent customer to apply rebates"""
        partner_id = self.env['res.partner'].sudo().browse(partner_id)
        if partner_id.is_parent:
            return partner_id
        partner = partner_id.parent_id.id
        while partner:
            partner = partner.parent_id.id
        if not partner:
            partner = partner_id
        return self.env['res.partner'].sudo().browse(partner.id)

    def _gather(self, partner_id, rebate_id, reverse=False, date_from=None, date_to=None):
        if not date_from:
            date_from = rebate_id.date_start
        if not date_to:
            date_to = rebate_id.date_end
        domain = [('partner_id', '=', partner_id.id), ('rebate_id', '=', rebate_id.id)]
        if date_from:
            domain += [('date_start', '<=', date_from)]
        if date_to:
            domain += [('date_end', '>=', date_to)]
        return self.search(domain, order='date_start' if reverse else 'date_start desc')

    def _get_customer_current_rebate(self, partner_id, rebate_id):
        partner = self._get_rebate_partner(partner_id.id)
        entries = self._gather(partner, rebate_id)
        entry = None
        if entries:
            self._cr.execute("SELECT id FROM rebate_entry WHERE id IN %s LIMIT 1 FOR NO KEY UPDATE SKIP LOCKED",
                             [tuple(entries.ids)])
            entry_result = self._cr.fetchone()
            if entry_result:
                entry = self.browse(entry_result[0])
        return entry or entries

    def _update_rebate(self, partner_id, rebate_id):
        self = self.sudo()
        partner = self._get_rebate_partner(partner_id.id)
        entry = self._get_customer_current_rebate(partner_id, rebate_id)
        invoiced_amount = 0.0
        rebate_items = entry.rebate_item_lines
        for item in rebate_items:
            move = item.invoice_line_id.move_id
            if move.move_type == 'out_refund':
                invoiced_amount -= item.amount
            else:
                invoiced_amount += item.amount
        rebate_values = partner._get_rebate_values(rebate_id, invoiced_amount)
        progressive_slab = rebate_values.get('progressive_slab', False)
        values = {
            'progressive_rebate_id': progressive_slab.id,
            'fixed_rebate_percentage': rebate_id.total_without_progressive,
            'progressive_rebate_percentage': progressive_slab.rebate_percentage if progressive_slab else 0.0,
            'total_rebate_progressive_amount': rebate_values.get('progressive_amount', 0.0),
            'entry_type': rebate_values.get('progressive_type', 'normal'),
        }
        total_amount = values.get('total_rebate_progressive_amount', 0.0) + rebate_values.get('fixed_rebate_total', 0.0)
        if entry:
            entry.write(values)
            entry._update_fixed_rebate_vals(rebate_values['fixed_rebate_vals'])
        else:
            if not float_is_zero(total_amount, precision_rounding=self.env.company.currency_id.rounding):
                values.update({
                    'rebate_id': rebate_id.id,
                    'partner_id': partner.id,
                    'fixed_rebate_lines': self._prepare_fixed_rebate_values(rebate_values['fixed_rebate_vals']),
                })
                entry = self.create(values)
        return entry

    def _update_fixed_rebate_vals(self, vals):
        lines_to_remove = self.fixed_rebate_lines.browse()
        existing_items = self.fixed_rebate_lines.mapped('fixed_rebate_id').ids
        value_keys = vals.keys()
        new_items = list(set(value_keys) - set(existing_items))
        for line in self.fixed_rebate_lines:
            # check the fixed rebate id still exist
            if line.fixed_rebate_id.id in value_keys:
                line.update({
                    'rebate_fixed_amount': vals[line.fixed_rebate_id.id],
                })
            else:
                lines_to_remove |= line
        lines_to_remove.unlink()
        new_vals = []
        for item in new_items:
            new_vals.append((0, 0, {
                'fixed_rebate_id': item,
                'rebate_fixed_amount': vals.get(item, 0.0)
            }))
        self.write({
            'fixed_rebate_lines': new_vals
        })
        return True

    def _prepare_fixed_rebate_values(self, vals):
        """Returns values to create rebate.fixed.entry.line from the given rebate"""

        new_vals = []
        for item in vals:
            new_vals.append((0, 0, {
                'fixed_rebate_id': item,
                'rebate_fixed_amount': vals.get(item, 0.0)
            }))
        return new_vals

    def _create_dummy_entry(self, vals):
        """
            Sometimes we are forced to crate a dummy rebate entry to make
            One2many relation with newly created rebate items
        """
        if vals.get('partner_id'):
            partner = self._get_rebate_partner(vals['partner_id'])
            vals.update({
                'partner_id': partner.id
            })
        entry = self.create(vals)
        return entry

    def _get_rebate_values(self, rebate, invoice_total=None):
        """
            returns current rebate position of the self(customer).
            pass context value include_child=False to get rebate of the partner without considering its children
         """
        slabs = rebate.progressive_ids.sorted('rebate_percentage', reverse=True)
        item_type = 'normal'
        if slabs:
            least_slabs = slabs.filtered(lambda l: l.target_val <= invoice_total)
            # get a slab where it reaches invoice total. if no slabs found, gets the slab with the highest slab value.
            if len(least_slabs) == 0:
                item_type = 'reservation'
            slab_id = least_slabs and least_slabs.sorted('target_val', reverse=True)[0] or slabs[0]
        else:
            slab_id = slabs
        fixed_vals = {}
        total_fixed_amount = 0.0
        for line in rebate.fixed_ids:
            amount = (line.percentage * invoice_total) / 100
            fixed_vals[line.id] = amount
            total_fixed_amount += amount
        return {
            'progressive_slab': slab_id,
            'progressive_amount': (slab_id.rebate_percentage * invoice_total) / 100,
            'fixed_rebate_vals': fixed_vals,
            'fixed_rebate_total': total_fixed_amount,
            'progressive_type': item_type,
        }

    def action_show_fixed_rebates(self):
        self.ensure_one()
        action = self.env.ref("kg_sarya_rebate.action_rebate_fixed_entry").sudo().read()[0]
        action["res_id"] = self.id
        return action

    def action_show_rebate_items(self):
        action = self.env.ref("kg_sarya_rebate.action_rebate_item").sudo().read()[0]
        action['target'] = 'current'
        action['context'] = {
            'search_default_groupby_invoice': 1
        }
        action["domain"] = [("rebate_entry_id", "in", self.ids)]
        return action

    def action_show_move_ids(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_moves_all_a')
        ids = self.move_ids.ids
        action['domain'] = [('id', 'in', ids)]
        return action

    def _prepare_progressive_rebate_move_vals(self, journal_id, credit_account, move_date):
        if not self:
            return False
        # we don't use progressive rebate name directly as it is
        # a computed field, and it's structure might not fit for move label.
        name = "Progressive rebate entry for %s %s" % (
            self.progressive_rebate_id.rebate_id.name, self.progressive_rebate_id.slab)
        lines = [
            # debit lines
            (0, 0, {
                'name': name,
                'account_id': self.progressive_rebate_id.account_id.id,
                'debit': self.total_rebate_progressive_amount,
                'rebate_entry_id': self.id,
                'partner_id': self.partner_id.id,
            }),
            # credit lines
            (0, 0, {
                'name': name,
                'account_id': int(credit_account),
                'credit': self.total_rebate_progressive_amount,
                'rebate_entry_id': self.id,
                'partner_id': self.partner_id.id,
            })
        ]
        move_vals = {
            'ref': 'Rebate Entry: %s' % self.name,
            'journal_id': int(journal_id),
            'rebate_type': 'progressive',
            'rebate_master_id': self.rebate_id.id,
            'date': move_date or fields.Date.context_today(self),
            'line_ids': lines
        }
        return move_vals

    def _create_progressive_rebate_account_move(self, move_date, is_auto=True):
        """
            create journal entries from the rebate entry.
            :param boolean is_auto: to identify this method is called from a cron action or a normal call
        """
        journal_id = self.env['ir.config_parameter'].sudo().get_param('kg_sarya_rebate.rebate_journal_id')
        provision_acc = self.env['ir.config_parameter'].sudo().get_param('kg_sarya_rebate.rebate_provision_account_id')
        if not journal_id or not provision_acc:
            if not is_auto:
                raise UserError(_("Please configure Rebate Journal and Rebate Provision account in settings"))
            else:
                _logger.warning("Scheduled action for rebate progressive entry is failed. "
                                "Please configure Rebate Journal and Rebate Provision account in settings")
        # objects of empty recordset  to reuse
        AccountMove = self.env['account.move']
        new_move_lines = self.env['account.move.line']
        AccountMoveLine = self.env['account.move.line']

        for entry in self.filtered(lambda e: e.progressive_rebate_id):
            # update current rebate entry to make sure we have the latest data
            entry._update_rebate(entry.partner_id, entry.rebate_id)
            progressive_move_ids = entry.move_ids.filtered(lambda mv: mv.parent_state == 'posted')
            if progressive_move_ids:
                move_name = "Progressive rebate entry for %s %s" % (
                    entry.progressive_rebate_id.rebate_id.name, entry.progressive_rebate_id.slab)
                previous_move_balance = sum(progressive_move_ids.mapped('balance'))
                progressive_amount = entry.total_rebate_progressive_amount
                if float_compare(previous_move_balance, progressive_amount,
                                 precision_rounding=self.currency_id.rounding) != 0:
                    # means there is a difference between previous account entries and current rebate.
                    domain = [('id', 'in', progressive_move_ids.ids)]
                    moves_by_accounts = AccountMoveLine.read_group(domain, ['account_id', 'balance'], ['account_id'])
                    revise_move_vals = []
                    for item in moves_by_accounts:
                        balance = abs(item['balance'])
                        if item['balance'] >= 0:
                            # probably, it will be a debit side line total
                            sign = -1 if balance > progressive_amount else 1
                        else:
                            # probably, it will be a debit side line total
                            sign = -1 if balance < progressive_amount else 1
                        amount = sign * (balance - progressive_amount)
                        credit = abs(amount) if amount < 0.0 else 0.0
                        debit = amount if amount >= 0.0 else 0.0
                        if debit or credit:
                            revise_move_vals.append((0, 0, {
                                'name': move_name,
                                'account_id': item['account_id'][0],
                                'debit': debit,
                                'credit': credit,
                                'rebate_entry_id': entry.id,
                                'partner_id': entry.partner_id.id,
                            }))
                    if revise_move_vals:
                        move_vals = {
                            'ref': 'Rebate Entry: %s' % self.name,
                            'journal_id': int(journal_id),
                            'date': move_date or fields.Date.context_today(self),
                            'rebate_type': 'progressive',
                            'rebate_master_id': self.rebate_id.id,
                            'line_ids': revise_move_vals,
                        }
                        move = AccountMove.create(move_vals)
                        move.action_post()
                        new_move_lines |= move.line_ids
            else:
                move_vals = entry._prepare_progressive_rebate_move_vals(int(journal_id), int(provision_acc), move_date)
                if move_vals:
                    progressive_move = AccountMove.create(move_vals)
                    progressive_move.action_post()
                    new_move_lines |= progressive_move.line_ids
        return new_move_lines


class RebateFixedEntryLine(models.Model):
    _name = "rebate.fixed.entry.line"
    _description = "Rebate Entries"
    _rec_name = 'fixed_rebate_id'

    parent_id = fields.Many2one('rebate.entry', 'Rebate Entry', ondelete='cascade')
    fixed_rebate_id = fields.Many2one('rebate.fixed.item', 'Fixed Rebate Item')
    currency_id = fields.Many2one(related='parent_id.currency_id')
    # related fields of fixed_rebate_id
    rebate_id = fields.Many2one(related='fixed_rebate_id.rebate_id')
    account_id = fields.Many2one(related='fixed_rebate_id.account_id')
    percentage = fields.Float(related='fixed_rebate_id.percentage')
    rebate_fixed_amount = fields.Monetary('Amount')
