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
        'data/ir_sequence_data.xml',
        'views/resources.xml',
        'views/partner_views.xml',
        'views/zaccount_invoice_views.xml',
        'views/zaccount_move_views.xml',
        'views/zreport_invoice.xml',
        'reports/paperformat.xml',
        'reports/reports.xml',
        'reports/report_invoice_customer.xml',
        'reports/report_invoice_or.xml',
        'reports/report_invoice_aab.xml',
        'reports/report_invoice_non_merimen.xml',
        'reports/report_vendor_billing_list.xml',
        'wizards/bill_vendor_view.xml',
    ],
    'installable': True,
    'auto_install': True,
    'application': False,
}
