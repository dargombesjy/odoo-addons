# -*- coding: utf-8 -*-
{
    'name': 'Custom Invoicing',
    'version': '1.0',
    'depends': ['account'],
    'author': 'Dargombes Djaja',
    'category': 'Uncategorized',
    'description': """
    Custom Invoicing
    """,
    'data': [
        'views/partner_views.xml',
        'views/zaccount_invoice_views.xml',
        'views/zreport_invoice.xml',
        'report/paperformat.xml',
        'report/reports.xml',
        'report/report_invoice_or.xml',
    ],
    'installable': True,
    'auto_install': True,
    'application': False,
}
