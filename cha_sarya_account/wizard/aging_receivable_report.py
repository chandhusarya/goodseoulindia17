from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from collections import OrderedDict
import io
from odoo.tools.misc import xlsxwriter

import logging
from odoo.tests import common

_logger = logging.getLogger(__name__)

try:
    from xlrd import open_workbook
except ImportError:
    _logger.debug("Can not import xlrd`.")

class SaryaAgingReceivable(models.TransientModel):
    """Sarya Aging Receivable"""

    _name = 'sarya.aging.receivable'
    _description = 'Sarya Aging Receivable'

    master_parent_id = fields.Many2one('master.parent', string="Master Parent")
    as_of_date = fields.Date("As of Date", required=True)


    def print_report(self):
        print("ddddddddddddddddddddd")



    def gen_report_value(self):

        report_value = {}

        #Find all customer or customer in master parent
        search_condition = []
        if self.master_parent_id:
            search_condition.append(('master_parent_id', '=', self.master_parent_id.id))
        all_partner = self.env['res.partner'].search(search_condition)

        master_parent_grouped = {}
        for partner in all_partner:
            master_parent_id = partner.master_parent_id.id
            if master_parent_id:
                print("hhhhhhhhhh")








