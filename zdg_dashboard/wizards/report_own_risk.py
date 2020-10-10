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
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    
    @api.multi
    def get_wizard_values(self, data):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['date_from', 'date_to'])[0]
        return self.env.ref('zdg_dashboard.report_own_risk').with_context(landscape=True, discard_logo_check=True).report_action(self, data=data)
    

class ReportOwnRisk(models.AbstractModel):
    _name = 'report.zdg_dashboard.template_report_own_risk'
    
    def _get_data(self, data):
        cr =self.env.cr
        sql = ('''SELECT s.name AS no_spk, s.own_risk_invoiced AS or_status,\
        s.service_advisor AS service_advisor, e.name AS no_plat, i.move_name AS invoice,\
        i.state AS inv_status, COALESCE(s.amount_own_risk, 0) AS total\
        FROM service_order s\
        LEFT JOIN service_equipment e ON (s.equipment_id=e.id)\
        LEFT JOIN account_invoice i ON (s.invoice_or_id=i.id)\
        WHERE s.finish_date >= %s AND s.finish_date <= %s ORDER BY inv_status, service_advisor, invoice''')
        
        params = [data['form']['date_from'], data['form']['date_to']]
        cr.execute(sql, params)
        
        results = {}
        lines = []
        totals = {
            'invoiced': {
                'paid': {
                    'count': 0,
                    'value': 0,
                },
                'open': {
                    'count': 0,
                    'value': 0,
                },
            },
            'not_invoiced': {
                'count': 0,
                'value': 0,
            }
        }
        for row in cr.dictfetchall():
            lines.append(row)
            if row['invoice']:
                if row['inv_status'] == 'paid':
                    totals['invoiced']['paid']['count'] += 1
                    totals['invoiced']['paid']['value'] += row['total']
                else:
                    totals['invoiced']['open']['count'] += 1
                    totals['invoiced']['open']['value'] += row['total']
            else:
                totals['not_invoiced']['count'] += 1
                totals['not_invoiced']['value'] += row['total']
            
        results['lines'] = lines
        results['totals'] = totals
        return results
    
    @api.model
    def _get_report_values(self, docids, data=None):
        docs = []
        data_results = self._get_data(data)
        return {
            'doc_ids': docids,
            'doc_model': data['model'],
            'data': data['form'],
            'docs': docs,
            'time': time,
            'results': data_results
        }