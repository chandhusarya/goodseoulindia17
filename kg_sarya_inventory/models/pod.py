from odoo import models, fields, _, api, SUPERUSER_ID
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_round, float_is_zero, groupby
from datetime import date

from datetime import datetime, timedelta,date
import time

from twilio.rest import Client
import json

class StockPickingPodUpload(models.TransientModel):
    _name = 'stock.picking.pod.upload'

    pod_attach_ids = fields.Many2many('ir.attachment', 'stock_picking_pod_upload_attachment', 'upload_id', 'attach_id',
                                      string="POD Attachments", required=True, copy=False)

    picking_id = fields.Many2one('stock.picking', string="Delivery Order", required=True, copy=False)


    def write(self, vals):
        print("\n\n\nvals =====>>>", vals)

        res = super(StockPickingPodUpload, self).write(vals)

        for rec in self:
            if rec.picking_id:
                rec.picking_id.pod_status = 'received'
                rec.picking_id.pod_attached_date = date.today()
                rec.picking_id.write({'pod_attach_ids': [(6, 0, rec.pod_attach_ids.ids)]})
                rec.picking_id.message_post(body="POD Attached Successfully")


                #update POD in invoice also

                if rec.picking_id.invoice_id:
                    rec.picking_id.invoice_id.write({'pod_attach_ids': [(6, 0, rec.pod_attach_ids.ids)]})
                    rec.picking_id.invoice_id.pod_status = 'received'
                    rec.picking_id.invoice_id.pod_attached_date = date.today()
                    rec.picking_id.invoice_id.message_post(body="POD Attached Successfully")






class StockPicking(models.Model):
    _inherit = 'stock.picking'

    pod_status = fields.Selection([('pending', 'Pending'),
                                   ('received', 'Received')],
                                  default='pending',
                                  string='POD Status',
                                  copy=False, tracking=True)

    delivery_status = fields.Selection([('ready_for_delivery', 'Ready for delivery'),
                                        ('out_for_delivery', 'Dispatched'),
                                        ('delivered', 'Delivered'),
                                        ('not delivered', 'Not delivered'),
                                        ('cancel', 'Cancelled')], default='ready_for_delivery', tracking=True)

    pod_attach_ids = fields.Many2many('ir.attachment', 'sarya_stockpick_attach_rel', 'pick_id', 'attach_id',
                                      string="POD Attachments", copy=False)

    pod_attached_date = fields.Date(string="POD Attached Date")

    def button_del_dipatched(self):
        self.write({'delivery_status': 'out_for_delivery'})
        self.invoice_id.write({'delivery_status_actual': 'out_for_delivery'})
        return True

    def button_del_undelivered(self):
        self.write({'delivery_status': 'not delivered'})
        self.invoice_id.write({'delivery_status_actual': 'not delivered'})
        return True

    def button_del_delivered(self):
        self.write({'delivery_status': 'delivered'})
        self.invoice_id.write({'delivery_status_actual': 'delivered'})
        return True

    def button_del_cancel(self):
        self.write({'delivery_status': 'cancel'})
        self.invoice_id.write({'delivery_status_actual': 'cancel'})
        return True

    def button_del_reset(self):
        self.write({'delivery_status': 'ready_for_delivery'})
        self.invoice_id.write({'delivery_status_actual': 'ready_for_delivery'})
        return True

    def upload_pod(self):
        self.ensure_one()

        upload_wizard = self.env['stock.picking.pod.upload'].create({
            'picking_id': self.id,
        })


        return {
            'type': 'ir.actions.act_window',
            'name': 'POD Upload',
            'view_mode': 'form',
            'res_model': 'stock.picking.pod.upload',
            'res_id': upload_wizard.id,
            'views': [(self.env.ref('kg_sarya_inventory.view_stock_picking_pod_upload_form').id, 'form')],
            'target': 'new',  # or 'current' if you don't want a popup
        }


