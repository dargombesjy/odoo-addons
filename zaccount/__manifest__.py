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
        # 'security/ir.model.access.csv',
        # 'views/account_report_settings.xml',
        # 'views/account_pdf_reports.xml',
        'views/partner_views.xml',
        'views/zaccount_invoice_views.xml',
        'views/zreport_invoice.xml',
        'reports/paperformat.xml',
        'reports/reports.xml',
        'reports/report_invoice_or.xml',
        'reports/report_invoice_aab.xml'
        # 'reports/report_general_ledger.xml',
        # 'wizards/general_ledger.xml',
    ],
    'installable': True,
    'auto_install': True,
    'application': False,
}
