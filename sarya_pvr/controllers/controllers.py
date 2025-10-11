# -*- coding: utf-8 -*-
from odoo import conf, http, _
from odoo.http import request
from odoo.exceptions import AccessError
from odoo.addons.portal.controllers.portal import CustomerPortal

class PortalPVRStockRequest(http.Controller):

    @http.route(['/my/stock/request'], type='http', auth='user', website=True)
    def portal_stock_request_render_backend_form(self, **kwargs):
        user = request.env['res.users'].sudo().search([('id', '=', request.uid)], limit=1)
        get_stock_request_action = user.sudo().action_open_stock_request_form()
        session_info = request.env['ir.http'].session_info()
        user_context = dict(request.env.context) if request.session.uid else {}
        mods = conf.server_wide_modules or []
        if request.env.lang:
            lang = request.env.lang
            session_info['user_context']['lang'] = lang
            user_context['lang'] = lang
        lang = user_context.get("lang")
        translation_hash = request.env['ir.http'].get_web_translations_hash(mods, lang)
        cache_hashes = {
            "translations": translation_hash,
        }
        session_info.update(
            cache_hashes=cache_hashes,
            action_name=get_stock_request_action,
            user_companies={
                'current_company': user.company_id.id,
                'allowed_companies': {
                    user.company_id.id: {
                        'id': user.company_id.id,
                        'name': user.company_id.name,
                    },
                },
            },
        )
        session_info['open_task_action'] = get_stock_request_action
        return request.render(
            'sarya_hr.action_render_embed',
            {'session_info': session_info},
        )

    @http.route(['/my/stock/current_available'], type='http', auth='user', website=True)
    def portal_stock_request_render_backend_tree(self, **kwargs):
        user = request.env['res.users'].sudo().search([('id', '=', request.uid)], limit=1)
        get_current_available_action = user.sudo().action_see_current_pvr_available()
        session_info = request.env['ir.http'].session_info()
        user_context = dict(request.env.context) if request.session.uid else {}
        mods = conf.server_wide_modules or []
        if request.env.lang:
            lang = request.env.lang
            session_info['user_context']['lang'] = lang
            user_context['lang'] = lang
        lang = user_context.get("lang")
        translation_hash = request.env['ir.http'].get_web_translations_hash(mods, lang)
        cache_hashes = {
            "translations": translation_hash,
        }
        session_info.update(
            cache_hashes=cache_hashes,
            action_name=get_current_available_action,
            user_companies={
                'current_company': user.company_id.id,
                'allowed_companies': {
                    user.company_id.id: {
                        'id': user.company_id.id,
                        'name': user.company_id.name,
                    },
                },
            },
        )
        session_info['open_task_action'] = get_current_available_action
        return request.render(
            'sarya_hr.action_render_embed',
            {'session_info': session_info},
        )

    @http.route(['/my/stock/grn_pending'], type='http', auth='user', website=True)
    def portal_stock_request_grn_pending_render_backend(self, **kwargs):
        user = request.env['res.users'].sudo().search([('id', '=', request.uid)], limit=1)
        get_grn_pending_records_action = user.sudo().action_see_grn_pending()
        session_info = request.env['ir.http'].session_info()
        user_context = dict(request.env.context) if request.session.uid else {}
        mods = conf.server_wide_modules or []
        if request.env.lang:
            lang = request.env.lang
            session_info['user_context']['lang'] = lang
            user_context['lang'] = lang
        lang = user_context.get("lang")
        translation_hash = request.env['ir.http'].get_web_translations_hash(mods, lang)
        cache_hashes = {
            "translations": translation_hash,
        }
        session_info.update(
            cache_hashes=cache_hashes,
            action_name=get_grn_pending_records_action,
            user_companies={
                'current_company': user.company_id.id,
                'allowed_companies': {
                    user.company_id.id: {
                        'id': user.company_id.id,
                        'name': user.company_id.name,
                    },
                },
            },
        )
        session_info['open_task_action'] = get_grn_pending_records_action
        return request.render(
            'sarya_hr.action_render_embed',
            {'session_info': session_info},
        )

    @http.route(['/my/stock_request_history'], type='http', auth='user', website=True)
    def portal_stock_request_history_render_backend(self, **kwargs):
        user = request.env['res.users'].sudo().search([('id', '=', request.uid)], limit=1)
        get_stock_request_history_action = user.sudo().action_see_stock_request_history()
        session_info = request.env['ir.http'].session_info()
        user_context = dict(request.env.context) if request.session.uid else {}
        mods = conf.server_wide_modules or []
        if request.env.lang:
            lang = request.env.lang
            session_info['user_context']['lang'] = lang
            user_context['lang'] = lang
        lang = user_context.get("lang")
        translation_hash = request.env['ir.http'].get_web_translations_hash(mods, lang)
        cache_hashes = {
            "translations": translation_hash,
        }
        session_info.update(
            cache_hashes=cache_hashes,
            action_name=get_stock_request_history_action,
            user_companies={
                'current_company': user.company_id.id,
                'allowed_companies': {
                    user.company_id.id: {
                        'id': user.company_id.id,
                        'name': user.company_id.name,
                    },
                },
            },
        )
        session_info['open_task_action'] = get_stock_request_history_action
        return request.render(
            'sarya_hr.action_render_embed',
            {'session_info': session_info},
        )
    
    @http.route(['/my/container/request'], type='http', auth='user', website=True)
    def portal_container_request_render_backend_form(self, **kwargs):
        user = request.env['res.users'].sudo().search([('id', '=', request.uid)], limit=1)
        get_container_request_action = user.sudo().action_open_container_request_form()
        session_info = request.env['ir.http'].session_info()
        user_context = dict(request.env.context) if request.session.uid else {}
        mods = conf.server_wide_modules or []
        if request.env.lang:
            lang = request.env.lang
            session_info['user_context']['lang'] = lang
            user_context['lang'] = lang
        lang = user_context.get("lang")
        translation_hash = request.env['ir.http'].get_web_translations_hash(mods, lang)
        cache_hashes = {
            "translations": translation_hash,
        }
        session_info.update(
            cache_hashes=cache_hashes,
            action_name=get_container_request_action,
            user_companies={
                'current_company': user.company_id.id,
                'allowed_companies': {
                    user.company_id.id: {
                        'id': user.company_id.id,
                        'name': user.company_id.name,
                    },
                },
            },
        )
        session_info['open_task_action'] = get_container_request_action
        return request.render(
            'sarya_hr.action_render_embed',
            {'session_info': session_info},
        )


    @http.route(['/my/container_request_history'], type='http', auth='user', website=True)
    def portal_container_request_history_render_backend(self, **kwargs):
        user = request.env['res.users'].sudo().search([('id', '=', request.uid)], limit=1)
        get_container_request_history_action = user.sudo().action_see_container_request_history()
        session_info = request.env['ir.http'].session_info()
        user_context = dict(request.env.context) if request.session.uid else {}
        mods = conf.server_wide_modules or []
        if request.env.lang:
            lang = request.env.lang
            session_info['user_context']['lang'] = lang
            user_context['lang'] = lang
        lang = user_context.get("lang")
        translation_hash = request.env['ir.http'].get_web_translations_hash(mods, lang)
        cache_hashes = {
            "translations": translation_hash,
        }
        session_info.update(
            cache_hashes=cache_hashes,
            action_name=get_container_request_history_action,
            user_companies={
                'current_company': user.company_id.id,
                'allowed_companies': {
                    user.company_id.id: {
                        'id': user.company_id.id,
                        'name': user.company_id.name,
                    },
                },
            },
        )
        session_info['open_task_action'] = get_container_request_history_action
        return request.render(
            'sarya_hr.action_render_embed',
            {'session_info': session_info},
        )


    @http.route(['/my/closing/sessions'], type='http', auth='user', website=True)
    def portal_closing_session_render_backend_form(self, **kwargs):
        user = request.env['res.users'].sudo().search([('id', '=', request.uid)], limit=1)
        get_closing_session_action = user.sudo().action_open_closing_session_request_form()
        session_info = request.env['ir.http'].session_info()
        user_context = dict(request.env.context) if request.session.uid else {}
        mods = conf.server_wide_modules or []
        if request.env.lang:
            lang = request.env.lang
            session_info['user_context']['lang'] = lang
            user_context['lang'] = lang
        lang = user_context.get("lang")
        translation_hash = request.env['ir.http'].get_web_translations_hash(mods, lang)
        cache_hashes = {
            "translations": translation_hash,
        }
        session_info.update(
            cache_hashes=cache_hashes,
            action_name=get_closing_session_action,
            user_companies={
                'current_company': user.company_id.id,
                'allowed_companies': {
                    user.company_id.id: {
                        'id': user.company_id.id,
                        'name': user.company_id.name,
                    },
                },
            },
        )
        session_info['open_task_action'] = get_closing_session_action
        return request.render(
            'sarya_hr.action_render_embed',
            {'session_info': session_info},
        )
    
    @http.route(['/my/container_grn_pending'], type='http', auth='user', website=True)
    def portal_container_request_grn_pending_render_backend(self, **kwargs):
        user = request.env['res.users'].sudo().search([('id', '=', request.uid)], limit=1)
        get_container_grn_pending_records_action = user.sudo().action_see_grn_pending_container()
        session_info = request.env['ir.http'].session_info()
        user_context = dict(request.env.context) if request.session.uid else {}
        mods = conf.server_wide_modules or []
        if request.env.lang:
            lang = request.env.lang
            session_info['user_context']['lang'] = lang
            user_context['lang'] = lang
        lang = user_context.get("lang")
        translation_hash = request.env['ir.http'].get_web_translations_hash(mods, lang)
        cache_hashes = {
            "translations": translation_hash,
        }
        session_info.update(
            cache_hashes=cache_hashes,
            action_name=get_container_grn_pending_records_action,
            user_companies={
                'current_company': user.company_id.id,
                'allowed_companies': {
                    user.company_id.id: {
                        'id': user.company_id.id,
                        'name': user.company_id.name,
                    },
                },
            },
        )
        session_info['open_task_action'] = get_container_grn_pending_records_action
        return request.render(
            'sarya_hr.action_render_embed',
            {'session_info': session_info},
        )

    @http.route(['/my/lpo_grn_pending'], type='http', auth='user', website=True)
    def portal_lpo_request_grn_pending_render_backend(self, **kwargs):
        user = request.env['res.users'].sudo().search([('id', '=', request.uid)], limit=1)
        get_lpo_grn_pending_records_action = user.sudo().action_see_lpo_grn_pending_container()
        session_info = request.env['ir.http'].session_info()
        user_context = dict(request.env.context) if request.session.uid else {}
        mods = conf.server_wide_modules or []
        if request.env.lang:
            lang = request.env.lang
            session_info['user_context']['lang'] = lang
            user_context['lang'] = lang
        lang = user_context.get("lang")
        translation_hash = request.env['ir.http'].get_web_translations_hash(mods, lang)
        cache_hashes = {
            "translations": translation_hash,
        }
        session_info.update(
            cache_hashes=cache_hashes,
            action_name=get_lpo_grn_pending_records_action,
            user_companies={
                'current_company': user.company_id.id,
                'allowed_companies': {
                    user.company_id.id: {
                        'id': user.company_id.id,
                        'name': user.company_id.name,
                    },
                },
            },
        )
        session_info['open_task_action'] = get_lpo_grn_pending_records_action
        return request.render(
            'sarya_hr.action_render_embed',
            {'session_info': session_info},
        )

    @http.route(['/my/container/transfer_pvr'], type='http', auth='user', website=True)
    def portal_container_transfer_pvr_render_backend_form(self, **kwargs):
        user = request.env['res.users'].sudo().search([('id', '=', request.uid)], limit=1)
        get_container_transfer_action = user.sudo().action_open_container_transfer_pvr_form()
        session_info = request.env['ir.http'].session_info()
        user_context = dict(request.env.context) if request.session.uid else {}
        mods = conf.server_wide_modules or []
        if request.env.lang:
            lang = request.env.lang
            session_info['user_context']['lang'] = lang
            user_context['lang'] = lang
        lang = user_context.get("lang")
        translation_hash = request.env['ir.http'].get_web_translations_hash(mods, lang)
        cache_hashes = {
            "translations": translation_hash,
        }
        session_info.update(
            cache_hashes=cache_hashes,
            action_name=get_container_transfer_action,
            user_companies={
                'current_company': user.company_id.id,
                'allowed_companies': {
                    user.company_id.id: {
                        'id': user.company_id.id,
                        'name': user.company_id.name,
                    },
                },
            },
        )
        session_info['open_task_action'] = get_container_transfer_action
        return request.render(
            'sarya_hr.action_render_embed',
            {'session_info': session_info},
        )

    @http.route(['/my/wastage_entry'], type='http', auth='user', website=True)
    def portal_wastage_entry_render_backend_form(self, **kwargs):
        user = request.env['res.users'].sudo().search([('id', '=', request.uid)], limit=1)
        get_wastage_entry_action = user.sudo().action_open_wastage_entry_pvr_form()
        session_info = request.env['ir.http'].session_info()
        user_context = dict(request.env.context) if request.session.uid else {}
        mods = conf.server_wide_modules or []
        if request.env.lang:
            lang = request.env.lang
            session_info['user_context']['lang'] = lang
            user_context['lang'] = lang
        lang = user_context.get("lang")
        translation_hash = request.env['ir.http'].get_web_translations_hash(mods, lang)
        cache_hashes = {
            "translations": translation_hash,
        }
        session_info.update(
            cache_hashes=cache_hashes,
            action_name=get_wastage_entry_action,
            user_companies={
                'current_company': user.company_id.id,
                'allowed_companies': {
                    user.company_id.id: {
                        'id': user.company_id.id,
                        'name': user.company_id.name,
                    },
                },
            },
        )
        session_info['open_task_action'] = get_wastage_entry_action
        return request.render(
            'sarya_hr.action_render_embed',
            {'session_info': session_info},
        )

class PortalUserType(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super()._prepare_portal_layout_values()
        user = request.env.user.sudo()

        # Default type
        user_type = "unknown"

        # Check if user is Employee
        employee = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
        if employee:
            user_type = "employee"
        elif user.partner_id.customer_rank > 0:  # Distributor (Customer)
            user_type = "distributor"
        # if 'grn_pending_count' in counters:
        domain = [('state', '=', 'pending')]
        values['grn_pending_count'] = request.env['pvr.stock.request'].search_count(domain)

        values.update({
            "user_type": user_type,
        })
        return values

