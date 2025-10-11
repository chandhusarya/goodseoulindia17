# -*- coding: utf-8 -*-
# from odoo import http


# class KgSaryaRebate(http.Controller):
#     @http.route('/kg_sarya_rebate/kg_sarya_rebate/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/kg_sarya_rebate/kg_sarya_rebate/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('kg_sarya_rebate.listing', {
#             'root': '/kg_sarya_rebate/kg_sarya_rebate',
#             'objects': http.request.env['kg_sarya_rebate.kg_sarya_rebate'].search([]),
#         })

#     @http.route('/kg_sarya_rebate/kg_sarya_rebate/objects/<model("kg_sarya_rebate.kg_sarya_rebate"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('kg_sarya_rebate.object', {
#             'object': obj
#         })
