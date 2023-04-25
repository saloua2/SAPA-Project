# -*- coding: utf-8 -*-
{
    'name': 'Retenue de garantie et prime CEE',
    'version': '1.2',
    'category': 'Sales/Sales',
    'summary': '',
    'sequence': -101,
    'description': """
    """,
    'depends': [
        'base',
        'account',
        'sale_management',
        'l10n_fr',
        'sale_subscription',
    ],
    'data': [
        'data/products.xml',
        'security/ir.model.access.csv',
        'views/sale_make_invoice_advance_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'views/retenue_garantie_views.xml',
        'views/prime_cee_views.xml',
        'views/account_menuitem.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sf_retenue_garantie/static/src/components/**/*',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
