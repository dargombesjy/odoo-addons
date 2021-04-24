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
        'reports/reports.xml',
        'reports/report_own_risk.xml',
        # 'views/resources.xml',
        'views/zdg_dashboard_view.xml',
        'views/zdg_portal_templates.xml',
        'wizards/wizard_own_risk.xml',
        'wizards/wizard_service_order.xml',
        'wizards/wizard_work_order.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
