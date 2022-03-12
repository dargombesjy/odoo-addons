# -*- coding: utf-8 -*-
from odoo import api, models

class ReportWorkOrderXlsx(models.AbstractModel):
    _name = 'report.zdg_dashboard.report_work_order_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def _get_orders(self, data):
        cr = self.env.cr

        sql = ('''SELECT s.name, s.company_id, s.bill_type, s.state, s.insurance_id, p.name AS partner_name,\
            s.register_date, s.received_date, s.planned_date, s.finish_date\
            FROM service_order s\
            LEFT JOIN res_partner p ON (s.insurance_id=p.id)\
            WHERE s.register_date >= %s AND s.register_date <= %s\
            ORDER BY s.state, s.name''')
        params = (data['form']['date_from'], data['form']['date_to'])
        # params = ('KMS01/0470/03/2021',)
        cr.execute(sql, params)

        states = [('draft', 'Quotation'), ('confirmed', 'Confirmed'), ('under_repair', 'Under Repair'),
            ('ready', 'Repair Done'), ('2binvoiced', 'To Be Invoiced'), ('done', 'Closed'), ('cancel', 'Cancelled'),]
        # states = data['form']['state']
        bill_types = {}
        for (k, v) in [('claim', 'Bill to Insurance'), ('self', 'Bill to Customer'),]:
            ty = {
                'name': k,
                'description': v,
                'aggregates': 0,  #dict((fn, 0.0) for fn in ['lt_total', 'lt_spk', 'lt_work']),
                'orders': {},
            }
            for (s, v) in states:
                ty['orders'][s] = {
                    'state_name': v,
                    'aggregates': 0,  #dict((fn, 0.0) for fn in ['lt_total', 'lt_spk', 'lt_work']),
                    'order_lines': [],
                }
            bill_types[k] = ty

        for row in cr.dictfetchall():
            state = row.pop('state')
            bill = row.pop('bill_type')
            bill_types[bill]['aggregates'] += 1
            bill_types[bill]['orders'][state]['aggregates'] += 1
            bill_types[bill]['orders'][state]['order_lines'].append(row)
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
        date_normal = workbook.add_format({
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

        sheet.write(1, 1, 'Rekap Order Status', bold_h4)
        sheet.write(2, 1, 'Date From')
        sheet.write(2, 2, objs['data']['date_from'])
        sheet.write(2, 3, 'Date To')
        sheet.write(2, 4, objs['data']['date_to'])

        row = 4
        col = 1
        if objs['data']['with_details']:
            col += 1
        sheet.write(row, col + 1, 'Jumlah SPK', bold_right)
        if objs['data']['with_details']:
            sheet.write(row, col + 2, 'Tgl. Masuk')
            sheet.write(row, col + 3, 'Tgl. Masuk Produksi')
            sheet.write(row, col + 4, 'Tgl. Est. Selesai')
            sheet.write(row, col + 5, 'Tgl. Selesai')
        
        row += 1
        for order in orders.items():
            col = 1
            sheet.write(row, col, order[1]['description'], bold_h4)
            if objs['data']['with_details']:
                col += 1
                if order[1]['name'] == 'claim': 
                    sheet.write(row, col, 'Insurance', bold_h4)
            agg = order[1]['aggregates']
            sheet.write(row, col + 1, agg, bold_h4)
            # sheet.write(row, col + 2, agg['lt_total'], bold_h4)
            
            row += 1
            for line_c in order[1]['orders'].items():
                col = 1
                sheet.write(row, col, '%s %s' % ('..', line_c[1]['state_name']), bold)
                if objs['data']['with_details']:
                    col += 1
                s = line_c[1]['aggregates']
                sheet.write(row, col + 1, s, number_bold)
                # sheet.write(row, col + 2, s['lt_total'], number_bold)

                if objs['data']['with_details']:
                    row += 1
                    for o in line_c[1]['order_lines']:
                        col = 1
                        sheet.write(row, col, '%s %s' % ('....', o['name']))
                        col += 1
                        if order[1]['name'] == 'claim':
                            sheet.write(row, col, o['partner_name'])
                        sheet.write(row, col + 2, o['register_date'], date_normal)
                        sheet.write(row, col + 3, o['received_date'], date_normal)
                        sheet.write(row, col + 4, o['planned_date'], date_normal)
                        sheet.write(row, col + 4, o['finish_date'], date_normal)
                        row += 1
                row += 1
            row += 1

        