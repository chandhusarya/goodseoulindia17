from odoo import models, _


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _create_returns(self):
        # Prevent copy of the carrier and carrier price when generating return picking
        # (we have no integration of returns for now)
        new_picking, pick_type_id = super(StockReturnPicking, self)._create_returns()
        picking = self.env['stock.picking'].browse(new_picking)
        params = self._context.get('params', {})
        if params.get('model', False) == 'sales.return.form':
            return_form_id = self.env['sales.return.form'].sudo().browse(params.get('id'))
            if return_form_id.exists():
                return_form_id.picking_ids |= picking
                old_refs = ["<a href=# data-oe-model=stock.picking data-oe-id=%s>%s</a>" % tuple(name_get)
                            for name_get in self.picking_id.name_get()]
                new_refs = ["<a href=# data-oe-model=stock.picking data-oe-id=%s>%s</a>" % tuple(name_get)
                        for name_get in picking.name_get()]
                message = _("A new return(%s) has been created from the delivery # : %s") % (
                    ','.join(new_refs), ','.join(old_refs))
                return_form_id.message_post(body=message)
                form_refs = ["<a href=# data-oe-model=sales.return.form data-oe-id=%s>%s</a>" % tuple(name_get)
                             for name_get in return_form_id.name_get()]
                form_message = _("This return delivery has been created from: %s") % ','.join(form_refs)
                picking.message_post(body=form_message)
        return new_picking, pick_type_id
