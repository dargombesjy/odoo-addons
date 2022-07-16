# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ReportServiceIncomeWizard(models.TransientModel):
    _name = 'service.report.service.income.wizard'
    _description = 'Report Service Income'

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    with_details = fields.Boolean(string="Details?", default=False)
    # state = fields.Many2many('service.state.selection', string="Status", required=True)
    # states = fields.Many2many('account.journal', string='States', required=True, default=lambda self: self.env['account.journal'].search([('company_id', '=', self.company_id.id)]))
    date_from = fields.Date(string='Start Date',default=fields.Date.today)
    date_to = fields.Date(string='End Date', default=fields.Date.today)

    def _print_report(self, data):
        records = self.env[data['model']].browse(data.get('ids', []))
        return self.env.ref('service.report_service_income').report_action(records, data)

    @api.multi
    def get_wizard_values(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['date_from', 'date_to', 'with_details', 'company_id'])[0]
        return self.with_context(discard_logo_check=True)._print_report(data)