# -*- coding: utf-8 -*-
# from odoo import http


# class OwlTest(http.Controller):
#     @http.route('/owl_test/owl_test', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/owl_test/owl_test/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('owl_test.listing', {
#             'root': '/owl_test/owl_test',
#             'objects': http.request.env['owl_test.owl_test'].search([]),
#         })

#     @http.route('/owl_test/owl_test/objects/<model("owl_test.owl_test"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('owl_test.object', {
#             'object': obj
#         })

