# -*- coding: utf-8 -*-
from odoo import models, fields, api
import time


class OwnRiskWizard(models.TransientModel):
    _name = 'zdg_dashboard.own.risk.wizard'
    _description = 'Own Risk monitoring Report'
    
    or_status = fields.Selection([('invoiced', 'Invoiced'),
                                  ('not_invoiced', 'Belum Invoiced'),
                                  ('all', 'Semua')
                                  ], string='Status OR', default='all')
    date_from = fields.Date(string='Date From', default=fields.Date.today)
    date_to = fields.Date(string='Date To', default=fields.Date.today)
    with_details = fields.Boolean(string="Details?", default=False)
    
    @api.multi
    def get_wizard_values(self, data):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['date_from', 'date_to','with_details'])[0]
        return self.env.ref('zdg_dashboard.report_own_risk').with_context(landscape=True, discard_logo_check=True).report_action(self, data=data)
        