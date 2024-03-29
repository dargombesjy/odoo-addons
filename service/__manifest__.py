# -*- coding: utf-8 -*-
{
    'name': 'Services',
    'version': '1.0',
    'category': 'Manufacturing',
    'summary': 'Service Order',
    'description': 'Service Order Repair',
    'depends': ['stock', 'sale_management', 'account', 'zaccount'],
    'data': [
        'security/service_security.xml',
        'security/ir.model.access.csv',
        # 'views/resources.xml',
        'views/service_views.xml',
        'views/equipment_views.xml',
        'views/service_entry_views.xml',
        'data/ir_config_parameter.xml',
        # 'data/ir_sequence_data.xml',
        # 'data/product_category.xml',
        'wizards/warning_message_wizard.xml',
        'wizards/report_cso_wizard.xml',
        'wizards/report_sa_wizard.xml',
        'wizards/report_service_income_wizard.xml',
        'report/paperformat.xml',
        'report/service_reports.xml',
        'report/service_layout.xml',
        'report/service_template_service_order.xml',
        'report/pass_keluar.xml',
        ],
    'images': [],
    'css': ['static/css/zstyle.css'],
    'license': 'AGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
