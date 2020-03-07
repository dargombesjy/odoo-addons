# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indonesian - Accounting Generic',
    'version': '1.1',
    'category': 'Localization',
    'description': """
This is the base module to manage the Indonesian accounting chart in Odoo.
==============================================================================

Install Indonesian generic chart of accounts.
    """,
    'depends': [
        'account',
    ],
    'data': [
        'data/account_data.xml',
        'data/l10n_id_chart_data.xml',
        'data/account.account.template.csv',
        'data/l10n_id_chart_post_data.xml',
        'data/account_tax_template_data.xml',
        'data/account_chart_template_data.xml',
    ],
    'uninstall_hook': 'uninstall_hook',
}
