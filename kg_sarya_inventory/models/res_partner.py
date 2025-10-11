from odoo import api, fields, models
from datetime import date, datetime, timedelta
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_clearing_agent = fields.Boolean("Is Clearing Agent")

    clearing_agents = fields.Many2many('res.partner', 'partner_clearing_agent_rel', 'id', 'agent_id', string='Clearing Agents')
