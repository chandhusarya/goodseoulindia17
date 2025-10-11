from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_child_partners(self):
        self.ensure_one()
        partners = self.with_context(active_test=False).search(
            [('id', 'child_of', self.id)])
        partners |= self
        return partners

    def _get_rebase_invoice_total(self, date_from=None, date_to=None, domain=None):
        if not self.ids:
            return 0

        all_partners_and_children = {}
        all_partner_ids = []
        for partner in self.filtered('id'):
            # price_total is in the company currency
            all_partners_and_children[partner] = self.with_context(active_test=False).search(
                [('id', 'child_of', partner.id)]).ids
            all_partner_ids += all_partners_and_children[partner]
        move_domain = [
            ('partner_id', 'in', all_partner_ids),
            ('state', 'not in', ['draft', 'cancel']),
            ('move_type', 'in', ('out_invoice', 'out_refund')),
        ]
        if date_from:
            move_domain += [('invoice_date', '>=', date_from)]
        if date_to:
            move_domain += [('invoice_date', '<=', date_to)]
        if domain:
            move_domain += domain
        price_totals = self.env['account.invoice.report'].read_group(move_domain, ['price_total'], ['partner_id'])
        total = 0.0
        for partner, child_ids in all_partners_and_children.items():
            total += sum(price['price_total'] for price in price_totals if price['partner_id'][0] in child_ids)
        return total

    def _get_rebase_invoice_values(self, date_from=None, date_to=None, domain=None):
        if not self.ids:
            return 0

        all_partners_and_children = {}
        all_partner_ids = []
        for partner in self.filtered('id'):
            # price_total is in the company currency
            all_partners_and_children[partner] = self.with_context(active_test=False).search(
                [('id', 'child_of', partner.id)]).ids
            all_partner_ids += all_partners_and_children[partner]
        move_domain = [
            ('partner_id', 'in', all_partner_ids),
            ('state', 'not in', ['draft', 'cancel']),
            ('move_type', 'in', ('out_invoice', 'out_refund')),
        ]
        if date_from:
            move_domain += [('invoice_date', '>=', date_from)]
        if date_to:
            move_domain += [('invoice_date', '<=', date_to)]
        if domain:
            move_domain += domain
        invoice_reports = self.env['account.invoice.report'].search(move_domain)
        invoice_vals = invoice_reports.read(['id', 'partner_id', 'move_id', 'product_id', 'price_total'])
        return invoice_vals

    def _get_rebate_values(self, rebate, invoice_total=None):
        """
            returns current rebate position of the self(customer).
            pass context value include_child=False to get rebate of the partner without considering its children
         """
        slabs = rebate.progressive_ids.sorted('rebate_percentage', reverse=True)
        entry_type = 'normal'
        if slabs:
            least_slabs = slabs.filtered(lambda l: l.target_val <= invoice_total)
            # get a slab where it reaches invoice total. if no slabs found, gets the slab with the highest slab value.
            if len(least_slabs) == 0:
                entry_type = 'reservation'
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
            'progressive_type': entry_type,
        }

    def _get_progressive_rebate_slab(self, rebate, amount=None):
        """returns current progressive rebate slab of the self(customer).
         If no slab reached, returns the highest one and a True value"""

        invoice_total = amount
        slabs = rebate.progressive_ids.sorted('rebate_percentage', reverse=True)
        item_type = 'normal'
        if slabs:
            least_slabs = slabs.filtered(lambda l: l.target_val <= invoice_total)
            # get a slab where it reaches invoice total. if no slabs found, gets the slab with the highest slab value.
            if len(least_slabs) == 0:
                item_type = 'reservation'
            slab_head = least_slabs and least_slabs.sorted('target_val', reverse=True)[0] or slabs[0]
            return slab_head, item_type
        return slabs[0] if slabs else slabs, item_type

    def update_rebate_with_children(self):
        self._update_customer_rebate_entry()

    def update_rebate_without_children(self):
        self._update_customer_rebate_entry(include_child=False)

    def _update_customer_rebate_entry(self, include_child=True):
        """
        This method updates/creates rebate entries of the customers(self) regardless of invoice and rebate.
        Here we consider all rebates and invoices of the given customers. It helps to update the customer current
        rebate status globally.
        params::
            include_child: if true(by default), includes its child partners invoice total as well to calculate rebate
        """

        RebateEntry = self.env['rebate.entry']
        for partner in self:
            rebate_ids = partner.mapped('property_product_pricelist.rebate_ids')
            for rebate in rebate_ids:
                RebateEntry._update_rebate(partner_id=partner, rebate_id=rebate, include_child=include_child)
