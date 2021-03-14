# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'DGBZ Accounting Reports',
    'version': '12.0.1.0.0',
    'category': 'Invoicing Management',
    'summary': 'Accounting Reports For Odoo 12',
    'sequence': '10',
    'author': 'Dargombes Djaja',
    'website': '',
    'depends': ['account'],
    'demo': [],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/report_menu_parent.xml',
        'views/report_settings.xml',
        'wizards/general_ledger.xml',
        'wizards/balance_sheet.xml',
        'wizards/profit_and_loss.xml',
        'reports/reports.xml',
        'reports/report_general_ledger.xml',
        'reports/report_financial.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'qweb': [],
}