# -*- coding: utf-8 -*-

{
    'name': 'Financial Report',
    'version': '1.0',
    'summary': 'Standard Financial Report',
    'author': 'Dargombes Djaja',
    'description': """
        Standard Financial Report
        """,
    'category': 'Accounting',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_financial_report_data.xml',
        'views/account_menuitem.xml',
        'views/account_view.xml',
        'views/report_financial.xml',
        'views/report_generalledger.xml',
#         'views/report_overdue.xml',
        'views/report_partnerledger.xml',
        'views/report_trialbalance.xml',
#         'views/res_config_view.xml',
#         'views/web_planner_data.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}