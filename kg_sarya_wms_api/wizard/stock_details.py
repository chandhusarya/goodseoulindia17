
from odoo import _, fields,api, models




class WMSStock(models.TransientModel):
    _name = 'wms.stock.details'
    _description = 'Stock Details'

    total_received = fields.Float(readonly=True)
    allocated = fields.Float(readonly=True)
    available = fields.Float(readonly=True)
    on_hold = fields.Float(readonly=True)
    on_hand = fields.Float(readonly=True)
    wms_product_id = fields.Integer(readonly=True)
