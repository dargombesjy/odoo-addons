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
    'depends': ['website', 'service'],
    'data': [
        'reports/report_own_risk.xml',
        # 'views/resources.xml',
        'views/zdg_dashboard_view.xml',
        'views/zdg_portal_templates.xml',
        'wizards/wizard_own_risk.xml'
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
