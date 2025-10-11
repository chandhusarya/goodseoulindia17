
import logging
_logger = logging.getLogger(__name__)

from odoo import models, fields, api,_
import logging


class sryCoveragePlan(models.Model):
    _name = 'sry.coverage.plan'
    _description = 'Coverage Plan'
    _rec_name = 'date'

    _order = "date asc"

    outlet_id = fields.Many2one('res.partner', string="Outlet")
    date = fields.Date(string="Date")
    coverage_id = fields.Many2one('sry.coverage.master', string="Master")
    cover_line_id = fields.Many2one('sry.coverage.master.line', string="Master Line")
    type = fields.Selection([('delivery', 'Delivery'), ('visit', 'Visit')], string="Type")

    plan_of = fields.Selection([('merchandiser', 'Merchandiser'), ('executive', 'Key Account Executive')], string="Plan For")


