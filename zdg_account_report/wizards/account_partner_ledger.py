# -*- coding: utf-8 -*-

from odoo import fields, models, _


class AccountPartnerLedger(models.TransientModel):
    _inherit = "account.common.partner.report"
    _name = "account.report.partner.ledger"
    _description = "Account Partner Ledger"

    date_from = fields.Date(string='Start Date',default=fields.Date.today)
    date_to = fields.Date(string='End Date', default=fields.Date.today)
    amount_currency = fields.Boolean("With Currency",
                                     help="It adds the currency column on report if the "
                                          "currency differs from the company currency.")
    reconciled = fields.Boolean('Reconciled Entries')

    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update({'reconciled': self.reconciled, 'amount_currency': self.amount_currency})
        return self.env.ref('zdg_account_report.action_report_partner_ledger').with_context(landscape=True).report_action(self, data=data)
