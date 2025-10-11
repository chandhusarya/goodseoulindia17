from odoo import models, _


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def reverse_moves(self, is_modify=False):
        res = super(AccountMoveReversal, self).reverse_moves(is_modify=False)
        params = self._context.get('params', {})
        if params.get('model', False) == 'sales.return.form':
            return_form_id = self.env['sales.return.form'].sudo().browse(params.get('id'))
            if return_form_id.exists():
                return_form_id.invoice_ids |= self.new_move_ids
                old_refs = ["<a href=# data-oe-model=account.move data-oe-id=%s>%s</a>" % tuple(name_get)
                            for name_get in self.move_ids.name_get()]
                new_refs = [
                    "<a href=# data-oe-model=account.move data-oe-id=%s>credit note</a>" % self.new_move_ids.id if self.new_move_ids else '']
                message = _("A new %s has been created from the invoice # : %s") % (
                    ','.join(new_refs), ','.join(old_refs))
                return_form_id.message_post(body=message)
                form_refs = ["<a href=# data-oe-model=sales.return.form data-oe-id=%s>%s</a>" % tuple(name_get)
                             for name_get in return_form_id.name_get()]
                form_message = _("This credit note has been created from: %s") % ','.join(form_refs)
                self.new_move_ids.message_post(body=form_message)
        return res
