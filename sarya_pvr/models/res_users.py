# -*- coding: utf-8 -*-
from odoo import models, fields, api

class PVRStockLocation(models.Model):
    _inherit = 'res.users'

    def action_stock_request(self):
        return {
            'view_mode': 'form',
            'res_model': 'pvr.stock.request',
            'type': 'ir.actions.act_window',
            'target': 'main',
        }

    def action_open_stock_request_form(self):
        action = self.action_stock_request()
        action['views'] = [[self.env.ref('sarya_pvr.view_pvr_stock_request_form_portal').id, 'form']]

        pvr_master = self.env['pvr.location.master'].sudo().search([('allowed_user_ids', 'in', [self.id])], limit=1)

        if pvr_master:
            lines = []
            for product in pvr_master.allowed_product_ids:
                qty_in_location = self.env['stock.quant'].sudo().search_read(
                    [('product_id', '=', product.id), ('location_id', '=', pvr_master.location_id.id)],
                    ['quantity'],
                    limit=1
                )
                qty_available_at_pvr = qty_in_location[0]['quantity'] if qty_in_location else 0
                packaging = self.env['product.packaging'].search([
                    ('product_id', '=', product.id), ('primary_unit', '=', True)], limit=1)
                primary_packaging_id = packaging and packaging.id
                vendor = product.seller_ids[0].partner_id.id if product.seller_ids else False
                lines.append((0, 0, {
                    'product_id': product.id,
                    'requested_qty': 0,
                    'qty_available_at_pvr': qty_available_at_pvr,
                    'packaging_id': primary_packaging_id,
                    'lpo_vendor_id': vendor,
                }))

            action['context'] = {
                'default_pvr_master': pvr_master.id,
                'default_pvr_location_id': pvr_master.location_id.id,
                'default_request_line_ids': lines,
            }

        return action

    def action_see_current_pvr_available(self):
        user = self.env.user
        pvr_master = self.env['pvr.location.master'].sudo().search(
            [('allowed_user_ids', 'in', user.id)], limit=1)

        action = {
            'name': 'Stocks Available',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.quant',
            'view_mode': 'tree,form',
            'domain': [('location_id', '=', pvr_master.location_id.id)],
            'context': {'create': False},
        }
        action['views'] = [
            [self.env.ref('sarya_pvr.view_pvr_stock_quant_tree').id, 'tree'],
        ]
        return action


    def action_see_grn_pending(self):
        user = self.env.user
        pvr_master = self.env['pvr.location.master'].sudo().search(
            [('allowed_user_ids', 'in', user.id)], limit=1)

        action = {
            'name': 'GRN Pending',
            'type': 'ir.actions.act_window',
            'res_model': 'pvr.stock.request',
            'view_mode': 'tree,form',
            'domain': [('state', '=', 'pending'), ('pvr_location_id', '=', pvr_master.location_id.id), ('local_purchase_ids', '=', False)],
            'context': {'create': False},
        }
        action['views'] = [
            [self.env.ref('sarya_pvr.view_pvr_stock_request_tree').id, 'tree'],
            [self.env.ref('sarya_pvr.view_pvr_stock_request_form_portal').id, 'form'],
        ]
        return action
    
    def action_see_stock_request_history(self):
        user = self.env.user
        pvr_master = self.env['pvr.location.master'].sudo().search(
            [('allowed_user_ids', 'in', user.id)], limit=1)

        action = {
            'name': 'Stock Request History',
            'type': 'ir.actions.act_window',
            'res_model': 'pvr.stock.request',
            'view_mode': 'tree,form',
            'domain': [('pvr_location_id', '=', pvr_master.location_id.id)],
            'context': {'create': False, 'edit': False},
        }
        action['views'] = [
            [self.env.ref('sarya_pvr.view_pvr_stock_request_tree').id, 'tree'],
            [self.env.ref('sarya_pvr.view_pvr_stock_request_form_portal').id, 'form'],
        ]
        return action
    
    def action_container_request(self):
        return {
            'view_mode': 'form',
            'res_model': 'container.request',
            'type': 'ir.actions.act_window',
            'target': 'main',
        }

    def action_open_container_request_form(self):
        action = self.action_container_request()
        action['views'] = [[self.env.ref('sarya_pvr.view_container_request_form_portal').id, 'form']]

        pvr_master = self.env['pvr.location.master'].sudo().search([('allowed_user_ids', 'in', [self.id])], limit=1)

        if pvr_master:
            lines = []
            for product in pvr_master.container_products:
                qty_in_location = self.env['stock.quant'].sudo().search_read(
                    [('product_id', '=', product.id), ('location_id', '=', pvr_master.pvr_management_location.id)],
                    ['quantity'],
                    limit=1
                )
                qty_available_at_pvr = qty_in_location[0]['quantity'] if qty_in_location else 0

                lines.append((0, 0, {
                    'product_id': product.id,
                    'requested_qty': 0,
                    'qty_available_at_pvr': qty_available_at_pvr,
                }))

            action['context'] = {
                'default_pvr_master': pvr_master.id,
                'default_pvr_location_id': pvr_master.location_id.id,
                # 'default_request_date': fields.Date.today(),
                'default_request_line_ids': lines,
            }

        return action
    
    def action_see_container_request_history(self):
        user = self.env.user
        pvr_master = self.env['pvr.location.master'].sudo().search(
            [('allowed_user_ids', 'in', user.id)], limit=1)

        action = {
            'name': 'Container Request History',
            'type': 'ir.actions.act_window',
            'res_model': 'container.request',
            'view_mode': 'tree,form',
            'domain': [('pvr_location_id', '=', pvr_master.location_id.id)],
            'context': {'create': False, 'edit': False},
        }
        action['views'] = [
            [self.env.ref('sarya_pvr.view_container_request_tree').id, 'tree'],
            [self.env.ref('sarya_pvr.view_container_request_form_portal').id, 'form'],
        ]
        return action

    def action_closing_sessions(self):
        return {
            'view_mode': 'form',
            'res_model': 'closing.session',
            'type': 'ir.actions.act_window',
            'target': 'main',
        }

    def action_open_closing_session_request_form(self):
        action = self.action_closing_sessions()
        action['views'] = [[self.env.ref('sarya_pvr.view_closing_session_request_form_portal').id, 'form']]

        pvr_master = self.env['pvr.location.master'].sudo().search([('allowed_user_ids', 'in', [self.id])], limit=1)

        if pvr_master:
            lines = []
            last_closing_dt = False
            last_closing = self.env['closing.session'].sudo().search([
                ("closing_datetime", "<", fields.Datetime.now()),
                ("state", "=", "done")
            ], order="closing_datetime desc", limit=1)
            if last_closing:
                last_closing_dt = last_closing.closing_datetime
            for product in pvr_master.container_products:
                request_domain = [("product_id", "=", product.id)]
                if last_closing_dt:
                    request_domain.append(("request_id.request_date", ">", last_closing_dt))
                request_domain.append(("request_id.request_date", "<=", fields.Datetime.now()))

                requested_qty = sum(
                    self.env["container.request.line"].search(request_domain).mapped("requested_qty")
                )
                if requested_qty > 0.0:
                    lines.append((0, 0, {
                        'product_id': product.id,
                        'qty_available_at_pvr': requested_qty,
                    }))

            action['context'] = {
                'default_pvr_master': pvr_master.id,
                'default_pvr_location_id': pvr_master.location_id.id,
                'default_request_line_ids': lines,
            }

        return action


    def action_see_grn_pending_container(self):
        user = self.env.user
        pvr_master = self.env['pvr.location.master'].sudo().search(
            [('allowed_user_ids', 'in', user.id)], limit=1)

        action = {
            'name': 'GRN Pending',
            'type': 'ir.actions.act_window',
            'res_model': 'container.request',
            'view_mode': 'tree,form',
            'domain': [('state', '=', 'pending'), ('pvr_location_id', '=', pvr_master.location_id.id)],
            'context': {'create': False},
        }
        action['views'] = [
            [self.env.ref('sarya_pvr.view_container_request_tree').id, 'tree'],
            [self.env.ref('sarya_pvr.view_container_request_form_portal_grn').id, 'form'],
        ]
        return action

    def action_see_lpo_grn_pending_container(self):
        """
        Return an action for portal users to see LPO GRN pending pickings.
        Only pickings linked to PVR LPO request.
        """
        user = self.env.user
        pvr_master = self.env['pvr.location.master'].sudo().search(
            [('allowed_user_ids', 'in', user.id)], limit=1
        )

        if not pvr_master:
            return {'type': 'ir.actions.act_window_close'}

        domain = [
            ('pvr_lpo_request_id', '!=', False),
            ('state', 'not in', ['done', 'cancel']),
            ('location_dest_id', '=', pvr_master.location_id.id)
        ]

        action = {
            'name': 'LPO GRN Pending',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {
                'create': False,
                'contact_display': 'partner_address', 'restricted_picking_type_code': 'incoming', 'search_default_reception': 1
            },
            'views': [
                [self.env.ref('sarya_pvr.vpicktree_sarya_pvr_portal').id, 'tree'],
                [self.env.ref('sarya_pvr.view_picking_form_sarya_portal').id, 'form'],
            ],
        }
        return action

    def action_container_transfer_pvr(self):
        return {
            'view_mode': 'form',
            'res_model': 'container.transfer.pvr',
            'type': 'ir.actions.act_window',
            'target': 'main',
        }

    def action_open_container_transfer_pvr_form(self):
        action = self.action_container_transfer_pvr()
        action['views'] = [[self.env.ref('sarya_pvr.view_container_transfer_form_portal').id, 'form']]

        # get master linked to user
        pvr_master = self.env['pvr.location.master'].sudo().search([('allowed_user_ids', 'in', [self.id])], limit=1)

        if pvr_master:
            lines = []
            for product in pvr_master.container_products:
                qty_in_location = self.env['stock.quant'].sudo().search_read(
                    [('product_id', '=', product.id), ('location_id', '=', pvr_master.location_id.id)],
                    ['quantity'],
                    limit=1
                )
                qty_available_at_pvr = qty_in_location[0]['quantity'] if qty_in_location else 0

                lines.append((0, 0, {
                    'product_id': product.id,
                    'requested_qty': 0,
                    'qty_available_at_pvr': qty_available_at_pvr,
                }))

            action['context'] = {
                'default_pvr_master': pvr_master.id,
                'default_pvr_location_id': pvr_master.location_id.id,
                # 'default_request_date': fields.Date.today(),
                'default_request_line_ids': lines,
            }

        return action
    
    def action_wastage_entry_pvr(self):
        return {
            'view_mode': 'form',
            'res_model': 'pvr.wastage.entry',
            'type': 'ir.actions.act_window',
            'target': 'main',
        }
    
    def action_open_wastage_entry_pvr_form(self):
        action = self.action_wastage_entry_pvr()
        action['views'] = [[self.env.ref('sarya_pvr.view_wastage_entry_form_portal').id, 'form']]

        # get master linked to user
        pvr_master = self.env['pvr.location.master'].sudo().search([('allowed_user_ids', 'in', [self.id])], limit=1)

        if pvr_master:
            lines = []
            for product in pvr_master.allowed_product_ids:
                print('product', product)
                qty_in_location = self.env['stock.quant'].sudo().search([
                    ("product_id", "=", product.id),
                    ("location_id", "in", [
                        pvr_master.location_id.id,
                        pvr_master.pvr_management_location.id
                    ])
                ])
                qty_available_at_pvr = sum(qty_in_location.mapped("quantity"))
                packaging = self.env['product.packaging'].search([
                    ('product_id', '=', product.id), ('primary_unit', '=', True)], limit=1)
                primary_packaging_id = packaging and packaging.id

                lines.append((0, 0, {
                    'product_id': product.id,
                    'wastage_qty': 0,
                    'total_stock': qty_available_at_pvr,
                }))

            action['context'] = {
                'default_pvr_master': pvr_master.id,
                'default_pvr_location_id': pvr_master.location_id.id,
                'default_packaging_id': primary_packaging_id,
                'default_line_ids': lines,
            }

        return action
