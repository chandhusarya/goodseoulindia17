
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from collections import OrderedDict
import io
from odoo.tools.misc import xlsxwriter

class ShipmentAdviceInspectionDate(models.TransientModel):
    """ShipmentAdviceInspectionDate"""

    _name = 'shipment.advice.inspection.date'
    _description = 'Shipment Advice Inspection Date'

    shipment_advice_id = fields.Many2one('shipment.advice', string='Shipment Advice')
    inspection_date = fields.Date("Inspection Date")


    def update_inspection(self):
        print("Update Inspection")
        self.shipment_advice_id.inspection_date = self.inspection_date
        self.shipment_advice_id.is_on_inspection = True