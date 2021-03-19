# -*- coding: utf-8 -*-
{
    'name': 'Custom Inventory',
    'version': '1.0',
    'depends': ['service'],
    'author': 'Dargombes Djaja',
    'category': 'Uncategorized',
    'description': """
    Custom Inventory
    """,
    'data': [
        'report/reports.xml',
        'views/inventory_views.xml',
        'views/zdg_product_template_view.xml',
        'wizards/stock_move_wizard.xml'
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
