{
    'name': 'KG Sarya',
    'version': '17.2',
    'category': 'Extra Tools',
    'summary': 'Sarya',
    'sequence': '10',
    'license': 'AGPL-3',
    'author': 'Christa',
    'maintainer': 'KG',
    'website': 'www.klystronglobal.com',
    'depends': ['base', 'base_geolocalize', 'sale_management', 'purchase', 'hr', 'stock', 'account',
                'account_accountant', 'product', 'sale', 'sale_margin', 'sh_pdc'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        # 'data/ir_cron.xml',
        'data/sales_category.xml',
        'data/pricelist_scheduler.xml',
        'data/rental_scheduler.xml',

        'views/region_master.xml',
        'views/master_parent.xml',
        'views/purchase_order.xml',

        'views/fright_charge_estimation.xml',

        'inherited_views/res_partner_inherit_view.xml',
        'inherited_views/price_list.xml',
        'inherited_views/sale_order.xml',
        'inherited_views/product_views.xml',

    ],
    'installable': True,
    'application': False,
    'auto_install': False,

}
