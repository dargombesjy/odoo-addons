# -*- coding: utf-8 -*-
{
    'name': 'Work',
    'version': '1.0',
    'category': 'Manufacturing',
    'summary': 'Work Order',
    'description': 'Work Order Repair',
    'depends': ['base', 'service'],
    'data': [
        'security/work_security.xml',
        'security/ir.model.access.csv',
        'views/work_views.xml',
        'views/work_stock_picking_views.xml',
        'report/work_reports.xml',
        'report/work_template_consumable_form.xml',
        'report/work_template_sparepart_form.xml',
        ],
    'images': [],
    'license': 'AGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
