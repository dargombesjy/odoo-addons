# -*- coding: utf-8 -*-
from odoo import api, models

class ReportServiceOrderXlsx(models.AbstractModel):
    _name = 'report.zdg_dashboard.report_service_order_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def _get_orders(self, data):
        cr = self.env.cr

        sql = ('''SELECT s.name, s.company_id, s.bill_type, s.state, s.equipment_id, e.name AS equipment_name,\
            s.amount_untaxed, s.cost_total, s.amount_own_risk, s.amount_sparepart, s.cost_operations,\
            s.amount_jasa, s.cost_bahan, s.amount_others, s.cost_others, s.amount_tax,\
            SUM(COALESCE(po.amount_untaxed,0)) AS jasa_untaxed, SUM(COALESCE(po.amount_total,0)) AS jasa_total\
            FROM service_order s\
            LEFT JOIN service_equipment e ON (s.equipment_id=e.id)\
            LEFT JOIN purchase_order po ON (s.id=po.service_id)\
            WHERE s.register_date >= %s AND s.register_date <= %s AND po.po_type = 'service'\
            GROUP BY s.name, s.company_id, s.bill_type, s.state, s.equipment_id, e.name, s.amount_untaxed,\
            s.cost_total, s.amount_own_risk, s.amount_sparepart, s.cost_operations,s.amount_jasa,\
            s.cost_bahan, s.amount_others, s.cost_others, s.amount_tax\
            ORDER BY s.state, s.name''')
        params = (data['form']['date_from'], data['form']['date_to'])
        # params = ('KMS01/0470/03/2021',)
        cr.execute(sql, params)

        states = [('draft', 'Quotation'), ('confirmed', 'Confirmed'), ('under_repair', 'Under Repair'),
            ('ready', 'Repair Done'), ('2binvoiced', 'To Be Invoiced'), ('done', 'Closed'),]
        # states = data['form']['state']
        bill_types = {}
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
            bill_types[k] = ty

        for row in cr.dictfetchall():
            state = row.pop('state')
            bill = row.pop('bill_type')
            # for item in bill_types:
            #     if item['name'] == bill:
            bill_types[bill]['aggregates']['amount_untaxed'] += row['amount_untaxed']
            bill_types[bill]['aggregates']['cost_total'] += row['cost_total']
            bill_types[bill]['aggregates']['margin'] += row['amount_untaxed'] - row['cost_total']
            bill_types[bill]['aggregates']['amount_sparepart'] += row['amount_sparepart']
            bill_types[bill]['aggregates']['cost_operations'] += row['cost_operations']
            bill_types[bill]['aggregates']['amount_jasa'] += row['amount_jasa']
            # bill_types[bill]['aggregates']['cost_fees'] += row['cost_fees']
            bill_types[bill]['aggregates']['cost_fees'] += row['jasa_untaxed']
            bill_types[bill]['aggregates']['cost_bahan'] += row['cost_bahan']
            bill_types[bill]['aggregates']['amount_others'] += row['amount_others']
            bill_types[bill]['aggregates']['cost_others'] += row['cost_others']
            bill_types[bill]['aggregates']['amount_tax'] += row['amount_tax']
            bill_types[bill]['aggregates']['amount_own_risk'] += row['amount_own_risk']
            bill_types[bill]['orders'][state]['aggregates']['amount_untaxed'] += row['amount_untaxed']
            bill_types[bill]['orders'][state]['aggregates']['cost_total'] += row['cost_total']
            bill_types[bill]['orders'][state]['aggregates']['margin'] += row['amount_untaxed'] - row['cost_total']
            bill_types[bill]['orders'][state]['aggregates']['amount_sparepart'] += row['amount_sparepart']
            bill_types[bill]['orders'][state]['aggregates']['cost_operations'] += row['cost_operations']
            bill_types[bill]['orders'][state]['aggregates']['amount_jasa'] += row['amount_jasa']
            # bill_types[bill]['orders'][state]['aggregates']['cost_fees'] += row['cost_fees']
            bill_types[bill]['orders'][state]['aggregates']['cost_fees'] += row['jasa_untaxed']
            bill_types[bill]['orders'][state]['aggregates']['cost_bahan'] += row['cost_bahan']
            bill_types[bill]['orders'][state]['aggregates']['amount_others'] += row['amount_others']
            bill_types[bill]['orders'][state]['aggregates']['cost_others'] += row['cost_others']
            bill_types[bill]['orders'][state]['aggregates']['amount_tax'] += row['amount_tax']
            bill_types[bill]['orders'][state]['aggregates']['amount_own_risk'] += row['amount_own_risk']
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
            # 'valign': 'vcenter',
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
            'bottom': 1
        })

        orders = objs['service_orders']

        sheet.hide_gridlines(2)
        sheet.set_column(0, 0, 2)
        sheet.set_column(1, 1, 22)
        sheet.set_column(2, 2, 10)
        sheet.set_column(3, 5, 15)
        sheet.set_column(6, 6, 2)
        sheet.set_column(7, 13, 15, None, {'level': 1})
        sheet.set_column(14, 14, 2, None, {'collapsed': True})
        sheet.set_column(15, 16, 15, None, {'level': 1})
        sheet.set_column(17, 17, 2, None, {'collapsed': True})

        sheet.write(1, 1, 'Estimasi Pendapatan Service Order', bold_h4)
        sheet.write(2, 1, '%s: %s' % ('Date From', objs['data']['date_from']))
        sheet.write(3, 1, '%s: %s' % ('Date To', objs['data']['date_to']))
        # sheet.write(2, 1, 'Date From')
        # sheet.write(2, 2, objs['data']['date_from'])
        # sheet.write(2, 3, 'Date To')
        # sheet.write(2, 4, objs['data']['date_to'])

        row = 5
        col = 1
        if objs['data']['with_details']:
            col += 1
        sheet.write(row, col + 1, 'Nilai SPK', bold_right)
        sheet.write(row, col + 2, 'Biaya SPK Total', bold_right)
        sheet.write(row, col + 3, 'Gain / Loss', bold_right)
        sheet.write(row, col + 5, 'Nilai Sparepart', bold_right)
        sheet.write(row, col + 6, 'Biaya Sparepart', bold_right)
        sheet.write(row, col + 7, 'Nilai Jasa', bold_right)
        sheet.write(row, col + 8, 'Biaya Borongan', bold_right)
        sheet.write(row, col + 9, 'Biaya Bahan', bold_right)
        sheet.write(row, col + 10, 'Pend. Lain2', bold_right)
        sheet.write(row, col + 11, 'Biaya Lain2', bold_right)
        sheet.write(row, col + 13, 'PPN', bold_right)
        sheet.write(row, col + 14, 'Pend. Own Risk', bold_right)
        # if objs['data']['with_details']:
        #     sheet.write(row, col + 16, 'Tgl. Masuk')
        #     sheet.write(row, col + 17, 'Tgl. Masuk Produksi')
        #     sheet.write(row, col + 18, 'Tgl. Selesai')
        
        row += 1
        for order in orders.items():
            col = 1
            sheet.write(row, col, order[1]['description'], bold_h4)
            if objs['data']['with_details']:
                col += 1
                sheet.write(row, col, 'No. Plat', bold_h4)
                # if order[1]['name'] == 'claim': 
                    # sheet.write(row, col, 'Insurance', bold_h4)
            # for agg in order[1]['aggregates'].items():
                # sheet.write(row, col, '%s %s' % (agg[0], agg[1]), bold_h4)
                # col += 1
            agg = order[1]['aggregates']
            sheet.write(row, col + 1, agg['amount_untaxed'], bold_h4)
            sheet.write(row, col + 2, agg['cost_total'], bold_h4)
            sheet.write(row, col + 3, agg['amount_untaxed'] - agg['cost_total'], bold_h4)
            sheet.write(row, col + 5, agg['amount_sparepart'], bold_h4)
            sheet.write(row, col + 6, agg['cost_operations'], bold_h4)
            sheet.write(row, col + 7, agg['amount_jasa'], bold_h4)
            sheet.write(row, col + 8, agg['cost_fees'], bold_h4)
            sheet.write(row, col + 9, agg['cost_bahan'], bold_h4)
            sheet.write(row, col + 10, agg['amount_others'], bold_h4)
            sheet.write(row, col + 11, agg['cost_others'], bold_h4)
            sheet.write(row, col + 13, agg['amount_tax'], bold_h4)
            sheet.write(row, col + 14, agg['amount_own_risk'], bold_h4)
            
            row += 1
            for line_c in order[1]['orders'].items():
                col = 1
                sheet.write(row, col, '%s %s' % ('..', line_c[1]['state_name']), bold)
                if objs['data']['with_details']:
                    col += 1
                # col += 1
                # for s in line_c[1]['aggregates'].items():
                #     sheet.write(row, col, s[1], number_bold)
                #     col += 1
                #     if s[0] == 'margin' or s[0] == 'cost_others':
                #         col += 1
                s = line_c[1]['aggregates']
                sheet.write(row, col + 1, s['amount_untaxed'], number_bold)
                sheet.write(row, col + 2, s['cost_total'], number_bold)
                sheet.write(row, col + 3, s['amount_untaxed'] - s['cost_total'], number_bold)
                sheet.write(row, col + 5, s['amount_sparepart'], number_bold)
                sheet.write(row, col + 6, s['cost_operations'], number_bold)
                sheet.write(row, col + 7, s['amount_jasa'], number_bold)
                sheet.write(row, col + 8, s['cost_fees'], number_bold)
                sheet.write(row, col + 9, s['cost_bahan'], number_bold)
                sheet.write(row, col + 10, s['amount_others'], number_bold)
                sheet.write(row, col + 11, s['cost_others'], number_bold)
                sheet.write(row, col + 13, s['amount_tax'], number_bold)
                sheet.write(row, col + 14, s['amount_own_risk'], number_bold)

                if objs['data']['with_details']:
                    row += 1
                    for o in line_c[1]['order_lines']:
                        col = 1
                        sheet.write(row, col, '%s %s' % ('....', o['name']))
                        col += 1
                        sheet.write(row, col, o['equipment_name'])
                        # if order[1]['name'] == 'claim':
                            # sheet.write(row, col, o['partner_name'])
                        sheet.write(row, col + 1, o['amount_untaxed'], number_normal)
                        sheet.write(row, col + 2, o['cost_total'], number_normal)
                        sheet.write(row, col + 3, o['amount_untaxed'] - o['cost_total'], number_normal)
                        sheet.write(row, col + 5, o['amount_sparepart'], number_normal)
                        sheet.write(row, col + 6, o['cost_operations'], number_normal)
                        sheet.write(row, col + 7, o['amount_jasa'], number_normal)
                        # sheet.write(row, col + 8, o['cost_fees'], number_normal)
                        sheet.write(row, col + 8, o['jasa_untaxed'], number_normal)
                        sheet.write(row, col + 9, o['cost_bahan'], number_normal)
                        sheet.write(row, col + 10, o['amount_others'], number_normal)
                        sheet.write(row, col + 11, o['cost_others'], number_normal)
                        sheet.write(row, col + 13, o['amount_tax'], number_normal)
                        sheet.write(row, col + 14, o['amount_own_risk'], number_normal)
                        # sheet.write(row, col + 16, o['register_date'], date_normal)
                        # sheet.write(row, col + 17, o['received_date'], date_normal)
                        # sheet.write(row, col + 18, o['finish_date'], date_normal)
                        sheet.set_row(row, None, None, {'level': 1})
                        row += 1
                        sheet.set_row(row, 3, None, {'collapsed': True})
                row += 1
            row += 1

        