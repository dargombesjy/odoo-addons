# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Odoo 12 Accounting PDF Reports',
    'version': '12.0.1.0.0',
    'category': 'Invoicing Management',
    'summary': 'Accounting Reports For Odoo 12',
    'sequence': '10',
    'author': 'Dargombes Djaja',
    'website': '',
    'depends': ['account'],
    'demo': [],
    'data': [
        'security/security.xml',
        'views/report_menu.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'qweb': [],
}