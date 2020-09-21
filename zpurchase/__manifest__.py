# -*- coding: utf-8 -*-
{
    'name': 'Custom purchase',
    'version': '1.0',
    'depends': ['product', 'purchase'],
    'author': 'Dargombes Djaja',
    'category': 'Uncategorized',
    'description': """
    Custom Purchasing
    """,
    'data': [
        'views/zpurchase_views.xml',
        'wizards/bill_vendor_view.xml'
    ],
    'installable': True,
    'auto_install': True,
    'application': False,
}
