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
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_make_invoice_advance_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
