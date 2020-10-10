# -*- coding: utf-8 -*-
{
    'name': 'Custom Dashboard',
    'version': '1.0',
    'depends': ['service'],
    'author': 'Dargombes Djaja',
    'category': 'Uncategorized',
    'description': """
    Custom Dashboard
    """,
    'data': [
        'reports/report_own_risk.xml',
        'views/zdg_dashboard_view.xml',
        'wizards/wizard_own_risk.xml'
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
