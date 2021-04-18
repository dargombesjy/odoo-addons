# -*- coding: utf-8 -*-
from odoo import models, fields, api
import time
from PIL.ImImagePlugin import number

class ReportOwnRiskXlsx(models.AbstractModel):
    _name = 'report.zdg_dashboard.report_own_risk_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def _get_data(self, data):
        cr =self.env.cr
        sql = ('''SELECT s.name AS no_spk, s.own_risk_invoiced AS or_status, s.state AS state,\
        s.service_advisor AS service_advisor, e.name AS no_plat, i.move_name AS invoice,\
        i.state AS inv_status, COALESCE(s.amount_own_risk, 0) AS total\
        FROM service_order s\
        LEFT JOIN service_equipment e ON (s.equipment_id=e.id)\
        LEFT JOIN account_invoice i ON (s.invoice_or_id=i.id)\
        WHERE s.register_date >= %s AND s.register_date <= %s\
        AND s.state IN (%s, %s, %s)\
        AND s.bill_type = %s\
        ORDER BY inv_status, service_advisor, invoice''')
        
        params = [data['form']['date_from'], data['form']['date_to'], 'ready', '2binvoiced', 'done', 'claim']
        cr.execute(sql, params)
        
        # results = {}
        # lines = []
        totals = {
            'invoiced': {
                'count': 0,
                'value': 0,
                'paid': {
                    'count': 0,
                    'value': 0,
                    'lines': []
                },
                'open': {
                    'count': 0,
                    'value': 0,
                    'lines': []
                },
            },
            'not_invoiced': {
                'count': 0,
                'value': 0,
                'lines': []
            }
        }
        for row in cr.dictfetchall():
            # lines.append(row)
            if row['invoice']:
                totals['invoiced']['count'] += 1
                totals['invoiced']['value'] += row['total']
                if row['inv_status'] == 'paid':
                    totals['invoiced']['paid']['count'] += 1
                    totals['invoiced']['paid']['value'] += row['total']
                    totals['invoiced']['paid']['lines'].append(row)
                else:
                    totals['invoiced']['open']['count'] += 1
                    totals['invoiced']['open']['value'] += row['total']
                    totals['invoiced']['open']['lines'].append(row)
            else:
                totals['not_invoiced']['count'] += 1
                totals['not_invoiced']['value'] += row['total']
                totals['not_invoiced']['lines'].append(row)
                
        return totals
        # results['lines'] = lines
        # results['totals'] = totals
        # return results
    
    @api.model
    def _get_objs_for_report(self, docids, data):
        self.model = self.env.context.get('active_model')
        results = self._get_data(data)
        return {
            'doc_ids': docids,
            'doc_model': self.model,
            'data': data['form'],
            'results': results 
        }

    def generate_xlsx_report(self, workbook, data, objs):
        sheet = workbook.add_worksheet('own_risk')
        number_normal = workbook.add_format({
            'num_format': '#,##0',
            # 'border': 1
        })
        number_bold = workbook.add_format({
            'num_format': '#,##0',
            'bold': True,
            # 'border': 1
        })
        date_format = workbook.add_format({
            'num_format': 'dd/mm/yyyy',
            # 'border': 1
        })
        bold_right = workbook.add_format({
            'bold': True,
            'align': 'right',
            # 'valign': 'center',
            # 'border': 1
        })
        bold = workbook.add_format({
            'bold': True,
            # 'align': 'right',
            # 'valign': 'center',
            # 'border': 1
        })
        bold_h4 = workbook.add_format({
            'font_size': 14,
            'bold': True,
            'num_format': '#,##0',
            # 'align': 'right',
            # 'valign': 'center',
            # 'border': 1
        })

        results = objs['results']
        states = {'ready': 'Repair Done', '2binvoiced': 'To Be Invoiced', 'done': 'Closed'}
        sheet.write(1, 1, 'Monitoring Own Risk', bold_h4)
        sheet.write(2, 1, 'Date From')
        sheet.write(2, 2, objs['data']['date_from'])
        sheet.write(2, 3, 'Date To')
        sheet.write(2, 4, objs['data']['date_to'])

        row = 4
        sheet.write(row, 1, 'Status', bold)
        # sheet.write(row, 2, 'Invoice Status', bold)
        sheet.write(row, 2, 'Jumlah SPK', bold)
        sheet.write(row, 3, 'Nilai', bold)
        if objs['data']['with_details']:
            # sheet.write(row, 4, 'No.SPK', bold)
            sheet.write(row, 4, 'No. Pol', bold)
            sheet.write(row, 5, 'No. Invoice', bold)
            sheet.write(row, 6, 'SA', bold)

        row += 1
        invoiced = results['invoiced']
        sheet.write(row, 1, 'Invoiced', number_bold)
        sheet.write(row, 2, invoiced['count'], number_bold)
        sheet.write(row, 3, invoiced['value'], number_bold)
        row += 1
        sheet.write(row, 1, '..Paid', number_normal)
        # sheet.write(row, 2, 'Paid', number_normal)
        sheet.write(row, 2, invoiced['paid']['count'], number_normal)
        sheet.write(row, 3, invoiced['paid']['value'], number_normal)
        if objs['data']['with_details']:
            for line in invoiced['paid']['lines']:
                row += 1
                sheet.write(row, 1, '%s %s' % ('....', line['no_spk']))
                sheet.write(row, 2, states[line['state']])
                sheet.write(row, 3, line['total'], number_normal)
                sheet.write(row, 4, line['no_plat'])
                sheet.write(row, 5, line['invoice'])
                sheet.write(row, 6, line['service_advisor'])
        row += 1
        sheet.write(row, 1, '..Open', number_normal)
        # sheet.write(row, 2, 'Open', number_normal)
        sheet.write(row, 2, invoiced['open']['count'], number_normal)
        sheet.write(row, 3, invoiced['open']['value'], number_normal)
        if objs['data']['with_details']:
            for line in invoiced['open']['lines']:
                row += 1
                sheet.write(row, 1, '%s %s' % ('....', line['no_spk']))
                sheet.write(row, 2, states[line['state']])
                sheet.write(row, 3, line['total'], number_normal)
                sheet.write(row, 4, line['no_plat'])
                sheet.write(row, 5, line['invoice'])
                sheet.write(row, 6, line['service_advisor'])
        row += 2
        not_invoiced = results['not_invoiced']
        sheet.write(row, 1, 'Belum Invoiced', number_bold)
        sheet.write(row, 2, not_invoiced['count'], number_bold)
        sheet.write(row, 3, not_invoiced['value'], number_bold)
        if objs['data']['with_details']:
            for line in not_invoiced['lines']:
                row += 1
                sheet.write(row, 1, '%s %s' % ('....', line['no_spk']))
                sheet.write(row, 2, states[line['state']])
                sheet.write(row, 3, line['total'], number_normal)
                sheet.write(row, 4, line['no_plat'])
                sheet.write(row, 5, line['invoice'])
                sheet.write(row, 6, line['service_advisor'])
        
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
        WHERE s.register_date >= %s AND s.register_date <= %s ORDER BY inv_status, service_advisor, invoice''')
        
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