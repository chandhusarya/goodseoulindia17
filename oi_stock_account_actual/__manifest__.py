# -*- coding: utf-8 -*-
# Copyright 2018 Openinside co. W.L.L.
{
    "name": "Actual Costing Method",
    "summary": "Costing at item level (Lot/serial No), Actual Costing Method, Real Costing Method, Product costing, Compute the cost of product, Inventory Valuation, Stock Valuation, Stock Removal Strategy, Material Costing, Calculate Real Cost, Lot, Serial Number, FIFO",
    "version": "17.10",
    'category': 'Warehouse',
    "website": "https://www.open-inside.com",
	"description": """
		Actual Costing Method		 
		Costing at item level (Lot/serial No)
    """,
	'images':[
        'static/description/cover.png'
	],
    "author": "Openinside",
    "license": "OPL-1",
    
    "installable": True,
    "depends": [
        'stock_account', 'purchase_stock'
    ],
    "data": [
        'view/product_template.xml',
        'view/product_category.xml',
        'view/stock_move.xml',
        'view/stock_valuation_layer.xml'
    ],
    'qweb' : [
           
        ],
    'odoo-apps' : True                   
}

