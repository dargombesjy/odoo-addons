# -*- coding: utf-8 -*-
from odoo import api, models

class ReportServiceOrderXlsx(models.AbstractModel):
    _name = 'report.zdg_dashboard.report_service_order_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def _get_orders(self, data):
        cr = self.env.cr

        sql = ('''SELECT s.name, s.company_id, s.bill_type, s.state, s.insurance_id, p.name as partner_name,\
            s.amount_untaxed, s.cost_total, s.amount_own_risk, s.amount_sparepart, s.cost_operations,\
            s.amount_jasa, s.cost_fees, s.cost_bahan, s.amount_others, s.cost_others, s.amount_tax\
            FROM service_order s\
            LEFT JOIN res_partner p ON (s.insurance_id=p.id)\
            WHERE s.register_date >= %s AND s.register_date <= %s ORDER BY s.id''')
        params = (data['form']['date_from'], data['form']['date_to'])
        cr.execute(sql, params)

        states = [('draft', 'Quotation'), ('confirmed', 'Confirmed'), ('under_repair', 'Under Repair'),
            ('ready', 'Repair Done'), ('2binvoiced', 'To Be Invoiced'), ('done', 'Closed'),]
        # states = data['form']['state']
        bill_types = []
        for (k, v) in [('claim', 'Bill to Insurance'), ('self', 'Bill to Customer'),]:
            ty = {
                'name': k,
                'description': v,
                'aggregates': dict((fn, 0.0) for fn in ['amount_untaxed', 'cost_total', 'margin',
                    'amount_sparepart', 'cost_operations', 'amount_jasa', 'cost_fees', 
                    'cost_bahan', 'amount_others', 'cost_others', 'amount_tax', 'amount_own_risk' ]),
                'orders': {},
            }
            for (s, v) in states:
                ty['orders'][s] = {
                    'state_name': v,
                    'aggregates': dict((fn, 0.0) for fn in ['amount_untaxed', 'cost_total', 'margin',
                        'amount_sparepart', 'cost_operations', 'amount_jasa', 'cost_fees', 
                        'cost_bahan', 'amount_others', 'cost_others', 'amount_tax', 'amount_own_risk' ]),
                    'order_lines': [],
                }
            bill_types.append(ty)

        for row in cr.dictfetchall():
            state = row.pop('state')
            bill = row.pop('bill_type')
            for item in bill_types:
                if item['name'] == bill:
                    item['aggregates']['amount_untaxed'] += row['amount_untaxed']
                    item['aggregates']['cost_total'] += row['cost_total']
                    item['aggregates']['margin'] += row['amount_untaxed'] - row['cost_total']
                    item['aggregates']['amount_sparepart'] += row['amount_sparepart']
                    item['aggregates']['cost_operations'] += row['cost_operations']
                    item['aggregates']['amount_jasa'] += row['amount_jasa']
                    item['aggregates']['cost_fees'] += row['cost_fees']
                    item['aggregates']['cost_bahan'] += row['cost_bahan']
                    item['aggregates']['amount_others'] += row['amount_others']
                    item['aggregates']['cost_others'] += row['cost_others']
                    item['aggregates']['amount_tax'] += row['amount_tax']
                    item['aggregates']['amount_own_risk'] += row['amount_own_risk']
                    item['orders'][state]['aggregates']['amount_untaxed'] += row['amount_untaxed']
                    item['orders'][state]['aggregates']['cost_total'] += row['cost_total']
                    item['orders'][state]['aggregates']['margin'] += row['amount_untaxed'] - row['cost_total']
                    item['orders'][state]['aggregates']['amount_sparepart'] += row['amount_sparepart']
                    item['orders'][state]['aggregates']['cost_operations'] += row['cost_operations']
                    item['orders'][state]['aggregates']['amount_jasa'] += row['amount_jasa']
                    item['orders'][state]['aggregates']['cost_fees'] += row['cost_fees']
                    item['orders'][state]['aggregates']['cost_bahan'] += row['cost_bahan']
                    item['orders'][state]['aggregates']['amount_others'] += row['amount_others']
                    item['orders'][state]['aggregates']['cost_others'] += row['cost_others']
                    item['orders'][state]['aggregates']['amount_tax'] += row['amount_tax']
                    item['orders'][state]['aggregates']['amount_own_risk'] += row['amount_own_risk']
                    item['orders'][state]['order_lines'].append(row)
        return bill_types

    @api.model
    def _get_objs_for_report(self, docids, data):
        self.model = self.env.context.get('active_model')
        orders = self._get_orders(data)
        return {
            'doc_ids': docids,
            'doc_model': self.model,
            'data': data['form'],
            'service_orders': orders 
        }

    def generate_xlsx_report(self, workbook, data, objs):
        sheet = workbook.add_worksheet('service_order')
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

        orders = objs['service_orders']

        sheet.write(1, 1, 'Estimasi Pendapatan Service Order', bold_h4)
        sheet.write(2, 1, 'Date From')
        sheet.write(2, 2, objs['data']['date_from'])
        sheet.write(2, 3, 'Date To')
        sheet.write(2, 4, objs['data']['date_to'])

        row = 4
        col = 2
        if objs['data']['with_details']:
            col += 1
        sheet.write(row, col, 'Pendapatan Sblm. Pajak', bold_right)
        col += 1
        sheet.write(row, col, 'Cost Total', bold_right)
        col += 1
        sheet.write(row, col, 'Margin', bold_right)
        col += 2
        sheet.write(row, col, 'Pend. Sparepart', bold_right)
        col += 1
        sheet.write(row, col, 'Cost Sparepart', bold_right)
        col += 1
        sheet.write(row, col, 'Pend. Jasa', bold_right)
        col += 1
        sheet.write(row, col, 'Biaya Borongan', bold_right)
        col += 1
        sheet.write(row, col, 'Biaya Bahan', bold_right)
        col += 1
        sheet.write(row, col, 'Pend. Lain2', bold_right)
        col += 1
        sheet.write(row, col, 'Biaya Lain2', bold_right)
        col += 2
        sheet.write(row, col, 'PPN', bold_right)
        col += 1
        sheet.write(row, col, 'Pend. Own Risk', bold_right)
        
        # claim
        row += 1
        for order in orders:
            col = 1
            sheet.write(row, col, order['description'], bold_h4)
            if objs['data']['with_details']:
                col += 1
            if order['name'] == 'claim': 
                sheet.write(row, col, 'Insurance', bold_h4)
            col += 1
            for agg_c in order['aggregates'].items():
                sheet.write(row, col, agg_c[1], bold_h4)
                col += 1
                if agg_c[0] == 'margin' or agg_c[0] == 'cost_others':
                    col += 1
            
            row += 1
            for line_c in order['orders'].items():
                col = 1
                sheet.write(row, col, '%s %s' % ('..', line_c[1]['state_name']), bold)
                if order['name'] == 'claim' and objs['data']['with_details']:
                    col += 1
                col += 1
                for s in line_c[1]['aggregates'].items():
                    sheet.write(row, col, s[1], number_bold)
                    col += 1
                    if s[0] == 'margin' or s[0] == 'cost_others':
                        col += 1
                if objs['data']['with_details']:
                    row += 1
                    for o in line_c[1]['order_lines']:
                        col = 1
                        sheet.write(row, col, '%s %s' % ('....', o['name']))
                        if order['name'] == 'claim':
                            col += 1
                            sheet.write(row, col, o['partner_name'])
                        col += 1
                        sheet.write(row, col, o['amount_untaxed'], number_normal)
                        col += 1
                        sheet.write(row, col, o['cost_total'], number_normal)
                        col += 1
                        sheet.write(row, col, o['amount_untaxed'] - o['cost_total'], number_normal)
                        col += 2
                        sheet.write(row, col, o['amount_sparepart'], number_normal)
                        col += 1
                        sheet.write(row, col, o['cost_operations'], number_normal)
                        col += 1
                        sheet.write(row, col, o['amount_jasa'], number_normal)
                        col += 1
                        sheet.write(row, col, o['cost_fees'], number_normal)
                        col += 1
                        sheet.write(row, col, o['cost_bahan'], number_normal)
                        col += 1
                        sheet.write(row, col, o['amount_others'], number_normal)
                        col += 1
                        sheet.write(row, col, o['cost_others'], number_normal)
                        col += 2
                        sheet.write(row, col, o['amount_tax'], number_normal)
                        col += 1
                        sheet.write(row, col, o['amount_own_risk'], number_normal)
                        row += 1
                row += 1
            row += 1

        