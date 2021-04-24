# -*- coding: utf-8 -*-
from odoo import models, fields, api

# STATES = [('draft', 'Quotation'),
#     ('cancel', 'Cancelled'),
#     ('confirmed', 'Confirmed'),
#     ('under_repair', 'Under Repair'),
#     ('ready', 'Repair Done'),
#     ('2binvoiced', 'To be Invoiced'),
#     ('invoice_except', 'Invoice Exception'),
#     ('done', 'Closed')]
#
# class StateSelection(models.model):
#     _name = 'zdg_dashboard.state.selection'
#     _rec_name = 'name'
#
#     name = fields.Char('Test')

class WorkOrderWizard(models.TransientModel):
    _name = 'zdg_dashboard.work.order.wizard'
    _description = 'Report Work Order'

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    with_details = fields.Boolean(string="Details?", default=False)
    # state = fields.Many2many('zdg_dashboard.state.selection', string="Status", required=True)
    # states = fields.Many2many('account.journal', string='States', required=True, default=lambda self: self.env['account.journal'].search([('company_id', '=', self.company_id.id)]))
    date_from = fields.Date(string='Start Date',default=fields.Date.today)
    date_to = fields.Date(string='End Date', default=fields.Date.today)

    def _print_report(self, data):
        records = self.env[data['model']].browse(data.get('ids', []))
        return self.env.ref('zdg_dashboard.report_work_order').report_action(records, data)

    @api.multi
    def get_wizard_values(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['date_from', 'date_to', 'with_details', 'company_id'])[0]
        # data['form']['state'] = self.read(['state',])
        return self.with_context(discard_logo_check=True)._print_report(data)