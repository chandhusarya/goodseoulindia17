from odoo import api, fields, models, _

from odoo.exceptions import UserError

class StockQuant(models.Model):
    """ The class StockQuant is used to inherit  stock.quant model  """
    _inherit = "stock.quant"

    lot_id = fields.Many2one(
        'stock.lot', 'LOT/Serial Number', index=True,
        ondelete='restrict', check_company=True,
        domain=lambda self: self._domain_lot_id())

    stock_inventory_id = fields.Many2one("stock.inventory", string="Stock inventory")

    def _apply_inventory(self):
        """Supering _apply_inventory"""
        for rec in self:
            if rec.stock_inventory_id:
                if not self.user_has_groups('stock.group_stock_manager'):
                    raise UserError(_('Only a stock manager can validate an inventory adjustment.'))
                rec.location_id.write({'last_inventory_date': fields.Date.today()})
                date_by_location = {loc: loc._get_next_inventory_date() for loc in rec.mapped('location_id')}
                for quant in rec:
                    quant.inventory_date = date_by_location[quant.location_id]
                # rec.write({'inventory_quantity': 0, 'user_id': False})
                # rec.write({'inventory_diff_quantity': 0})
                return False
            else:
                return super(StockQuant, self)._apply_inventory()
