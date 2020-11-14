# -*- coding: utf-8 -*-
{
    'name': 'Custom Data Administration',
    'version': '1.0',
    'depends': ['base'],
    'author': 'Dargombes Djaja',
    'category': 'Uncategorized',
    'description': """
    Custom Invoicing
    """,
    'data': [
        'security/admin_security.xml',
        'views/admin_view.xml',
    ],
    'installable': True,
    'auto_install': True,
    'application': False,
}