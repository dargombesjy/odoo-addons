# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountReportGeneralLedger(models.TransientModel):
    _inherit = "account.common.account.report"
    _name = "account.report.general.ledger"
    _description = "General Ledger Report"

    date_from = fields.Date(string='Start Date',default=fields.Date.today)
    date_to = fields.Date(string='End Date', default=fields.Date.today)
    initial_balance = fields.Boolean(string='Include Initial Balances',
                                    help='If you selected date, this field allow you to add a row to display the amount of debit/credit/balance that precedes the filter you\'ve set.')
    sortby = fields.Selection([('sort_date', 'Date'), ('sort_journal_partner', 'Journal & Partner')], string='Sort by', required=True, default='sort_date')
    report_type = fields.Selection([('cashflow', 'Cash Flow'),
                                    ('balance', 'Balance Sheet'),
                                    ('profitloss', 'Profit Loss'),
                                    ('all', 'All Entries'),
                                    ], string='Report Type', required=True, default='all')
    journal_ids = fields.Many2many('account.journal', 'account_report_general_ledger_journal_rel', 'account_id', 'journal_id', string='Journals', required=True)
    account_ids = fields.Many2many('account.account', string='Accounts', default=lambda self: self.env['account.account'].search(['&', ('company_id', '=', self.company_id.id), ('deprecated', '=', False)]))
    account_type_ids = fields.Many2many('account.account.type', string='Account Type', default=lambda self: self.env['account.account.type'].search([]))  #('type', '=', 'asset')]))

    @api.onchange('report_type')
    def _onchange_report_type(self):
        if self.report_type == 'cashflow':
            self.journal_ids = self.env['account.journal'].search([('type', 'in', ('cash', 'bank'))])
            self.account_type_ids = self.env['account.account.type'].search([('type', '=', 'liquidity')])
        elif self.report_type == 'balance':
            self.journal_ids = self.env['account.journal'].search([('type', 'not in', ('general',))])
            self.account_type_ids = self.env['account.account.type'].search([('internal_group', 'not in', ('income', 'expense'))])
        elif self.report_type == 'profitloss':
            self.journal_ids = self.env['account.journal'].search([('type', 'not in', ('general',))])
            self.account_type_ids = self.env['account.account.type'].search([('internal_group', 'in', ('income', 'expense'))])
        
        self.account_ids = self.env['account.account'].search([('user_type_id', 'in', self.account_type_ids.ids)])
    
    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update(self.read(['initial_balance', 'sortby', 'report_type', 'account_ids', 'account_type_ids'])[0])
        if data['form'].get('initial_balance') and not data['form'].get('date_from'):
            raise UserError(_("You must define a Start Date"))
        records = self.env[data['model']].browse(data.get('ids', []))
        return self.env.ref('zdg_account_report.action_report_general_ledger').with_context(landscape=True).report_action(records, data=data)
