# -*- coding: utf-8 -*-
{
    'name': 'Services',
    'version': '1.0',
    'category': 'Manufacturing',
    'summary': 'Service Order',
    'description': 'Service Order Repair',
    'depends': ['stock', 'sale_management', 'account'],
    'data': [
        'security/service_security.xml',
        'security/ir.model.access.csv',
        'views/service_views.xml',
        'views/equipment_views.xml',
        'views/partner_views.xml',
        'data/ir_sequence_data.xml',
        'report/service_reports.xml',
        'report/service_template_service_order.xml',
        ],
    'images': [],
    'license': 'AGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
