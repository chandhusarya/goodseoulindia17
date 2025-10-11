from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
import json
import base64
from datetime import date


class PortalSaleOrder(CustomerPortal):

    @http.route(['/my/new_sale_order'], type='http', auth="user", website=True)
    def portal_sale_order_form(self, **kwargs):
        """Render Empty Sale Order Form for Portal Users"""
        partner = request.env.user.partner_id
        pricelist = partner.property_product_pricelist
        product_tmpls = pricelist.item_ids.mapped('product_tmpl_id.id')
        products = request.env['product.product'].search([('product_tmpl_id', 'in', product_tmpls)])
        delivery_addresses = request.env['res.partner'].sudo().search([
            '|', ('parent_customer_id', '=', partner.id), ('id', '=', partner.id)
        ])
        print("partner", partner.id)
        print("delivery_addresses", delivery_addresses)

        return request.render('sry_customer_portal.portal_sale_order_form', {
            'partner': partner,
            'total_due': partner.total_due,
            'pricelist': pricelist,
            'products': products,
            'delivery_addresses': delivery_addresses,

        })

    @http.route(['/my/new_sale_order/submit'], type='http', auth="user", methods=['POST'], website=True)
    def submit_sale_order(self, **post):
        """Handles Order Submission and Creates Sales Order"""
        partner = request.env.user.partner_id
        pricelist = partner.property_product_pricelist
        lpo_date = post.get("lpo_date")
        lpo_no = post.get("lpo_no")
        note = post.get("note")
        delivery_date = post.get("delivery_date")
        delivery_address_id = int(post.get("delivery_address_id", partner.id))
        order_lines = []



        total_amount = 0
        for key, value in post.items():
            if key.startswith('product_') and value:
                line_id = key.split('_')[1]  # Extract line index
                product_id = int(value)
                quantity = float(post.get(f'quantity_{line_id}', 0))

                package_id = int(post.get(f'package_{line_id}', 0)) if post.get(f'package_{line_id}') else False

                product = request.env['product.product'].browse(product_id)
                price = pricelist._get_product_price(product, quantity, partner)

                package = request.env['product.packaging'].browse(package_id)

                order_lines.append((0, 0, {
                    'product_id': product.id,
                    'product_packaging_qty': quantity,
                    'pkg_unit_price': price,
                    'price_unit': price / package.qty,
                    'product_packaging_id': package_id if package_id else False,
                }))

                total_amount += price * quantity

        # Check if the total amount exceeds the credit limit
        if (total_amount + partner.total_due) > partner.credit_limit:
            return request.render("sry_customer_portal.portal_sale_order_failed", {
                "error_message": "Credit limit exceeded. Please contact your account manager."
            })

        if order_lines:
            partner_invoice_id = partner
            trade_channel = partner.trade_channel and partner.trade_channel.id or False
            journal = partner.trade_channel and partner.trade_channel.journal and partner.trade_channel.journal.id or False
            order_vals = {
                'partner_id': partner.id,
                'partner_invoice_id': partner.id,
                'partner_shipping_id': delivery_address_id,
                'order_line': order_lines,
                'pricelist_id': pricelist.id,
                'picking_type_id': partner.picking_type_id.id,
                'customer_lpo_date': lpo_date,
                'commitment_date': delivery_date,
                'trade_channel': trade_channel,
                'journal_id': journal,
                'client_order_ref': lpo_no,
                'payment_term_id': partner.property_payment_term_id and partner.property_payment_term_id.id or False,
            }
            sale_order = request.env['sale.order'].sudo().create(order_vals)
            for order_line in sale_order.order_line:
                # order_line._onchange_pkg_qty()
                order_line._onchange_product_packaging_id()
                order_line._onchange_update_product_packaging_qty()
                order_line._onchange_pkg_qty()

            sale_order.onchange_commitment_date_so()
            if note:
                sale_order.message_post(body=note)
            file = request.httprequest.files.get('attachment')
            if file:
                file_content = file.read()
                attachment = request.env['ir.attachment'].sudo().create({
                    'name': file.filename,
                    'datas': base64.b64encode(file_content),
                    'res_model': 'sale.order',
                    'res_id': sale_order.id,
                    'mimetype': file.content_type
                })
                if attachment:
                    sale_order.lpo_attach_id = [attachment.id]
            sale_order.send_quotation_approval_email()
            return request.redirect('/my/orders/%s' % sale_order.id)

        else:
            return request.render("sry_customer_portal.portal_sale_order_failed", {
                "error_message": "No products selected."
            })


    # @http.route(['/my/new_sale_order/submit'], type='http', auth="user", methods=['POST'], website=True)
    # def submit_sale_order(self, **post):
    #     """Handles Order Submission and Creates Sales Order"""
    #     partner = request.env.user.partner_id
    #     pricelist = partner.property_product_pricelist
    #     lpo_date = post.get("lpo_date")
    #     lpo_no = post.get("lpo_no")
    #     note = post.get("note")
    #     delivery_date = post.get("delivery_date")
    #     delivery_address_id = int(post.get("delivery_address_id", partner.id))
    #     order_lines = []
    #
    #
    #     try:
    #
    #         total_amount = 0
    #         for key, value in post.items():
    #             if key.startswith('product_') and value:
    #                 line_id = key.split('_')[1]  # Extract line index
    #                 product_id = int(value)
    #                 quantity = float(post.get(f'quantity_{line_id}', 0))
    #
    #                 package_id = int(post.get(f'package_{line_id}', 0)) if post.get(f'package_{line_id}') else False
    #
    #                 product = request.env['product.product'].browse(product_id)
    #                 price = pricelist._get_product_price(product, quantity, partner)
    #
    #                 package = request.env['product.packaging'].browse(package_id)
    #
    #                 order_lines.append((0, 0, {
    #                     'product_id': product.id,
    #                     'product_packaging_qty': quantity,
    #                     'pkg_unit_price': price,
    #                     'price_unit': price/package.qty,
    #                     'product_packaging_id': package_id if package_id else False,
    #                 }))
    #
    #                 total_amount += price * quantity
    #
    #         # Check if the total amount exceeds the credit limit
    #         if (total_amount + partner.total_due) > partner.credit_limit:
    #             return request.render("sry_customer_portal.portal_sale_order_failed", {
    #                 "error_message": "Credit limit exceeded. Please contact your account manager."
    #             })
    #
    #
    #         if order_lines:
    #             partner_invoice_id = partner
    #             trade_channel = partner.trade_channel and partner.trade_channel.id or False
    #             journal = partner.trade_channel and partner.trade_channel.journal and partner.trade_channel.journal.id or False
    #             order_vals = {
    #                 'partner_id': partner.id,
    #                 'partner_invoice_id': partner.id,
    #                 'partner_shipping_id': delivery_address_id,
    #                 'order_line': order_lines,
    #                 'pricelist_id': pricelist.id,
    #                 'picking_type_id': partner.picking_type_id.id,
    #                 'customer_lpo_date': lpo_date,
    #                 'commitment_date': delivery_date,
    #                 'trade_channel': trade_channel,
    #                 'journal_id':  journal,
    #                 'client_order_ref': lpo_no,
    #                 'payment_term_id': partner.property_payment_term_id and partner.property_payment_term_id.id or False,
    #             }
    #             sale_order = request.env['sale.order'].sudo().create(order_vals)
    #             for order_line in sale_order.order_line:
    #                 # order_line._onchange_pkg_qty()
    #                 order_line._onchange_product_packaging_id()
    #                 order_line._onchange_pkg_qty()
    #                 order_line._onchange_update_product_packaging_qty()
    #             sale_order.onchange_commitment_date_so()
    #             if note:
    #                 sale_order.message_post(body=note)
    #             file = request.httprequest.files.get('attachment')
    #             if file:
    #                 file_content = file.read()
    #                 attachment = request.env['ir.attachment'].sudo().create({
    #                     'name': file.filename,
    #                     'datas': base64.b64encode(file_content),
    #                     'res_model': 'sale.order',
    #                     'res_id': sale_order.id,
    #                     'mimetype': file.content_type
    #                 })
    #                 if attachment:
    #                     sale_order.lpo_attach_id = [attachment.id]
    #             sale_order.send_quotation_approval_email()
    #             return request.redirect('/my/orders/%s' % sale_order.id)
    #
    #         else:
    #             return request.render("sry_customer_portal.portal_sale_order_failed", {
    #                 "error_message": "No products selected."
    #             })
    #     except Exception as e:
    #         return request.render("sry_customer_portal.portal_sale_order_failed", {
    #             "error_message": str(e)
    #         })


    @http.route(['/my/new_sale_order/get_packages'], type='json', auth="user")
    def get_product_packages(self):
        """Fetch available packaging options for the selected product"""
        data = json.loads(request.httprequest.data)
        product_id = int(data.get('product_id', 0))
        product = request.env['product.product'].browse(int(product_id))
        packages = product.packaging_ids.filtered(lambda p: p.name == 'CARTON')  # Fetch packages linked to the product
        partner = request.env.user.partner_id
        pricelist = partner.property_product_pricelist

        package_list = []
        for package in packages:
            package_list.append({
                'id': package.id,
                'name': package.name,
                'pricelist': pricelist.id,
            })
        return {'packages': package_list}

    @http.route(['/my/new_sale_order/get_package_price'], type='json', auth="user")
    def get_package_price(self):
        """Fetch available packaging options for the selected product"""
        data = json.loads(request.httprequest.data)
        package_id = int(data.get('package_id', 0))
        pricelist_id = int(data.get('pricelist_id', 0))
        package = request.env['product.packaging'].browse(int(package_id))
        product_tmpl = package.product_id and package.product_id.product_tmpl_id
        price = 0
        pricelists = request.env['product.pricelist'].compute_price_rule_get_package_items \
            ([product_tmpl.id], pricelist_id, package_id)
        if pricelists:
            price = pricelists[0].fixed_price

        return {'price': price, 'mrp': package.product_id.list_price}