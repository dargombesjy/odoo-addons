from odoo import api, models


class ReportCsoXlsx(models.AbstractModel):
    _name = 'report.service.report_cso_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def _get_orders(self, data):
        cr = self.env.cr
        
        sql = ('''SELECT s.name, s.company_id, s.bill_type, s.insurance_id, s.service_advisor1, s.status_unit,
            i.insurance_name, p.sa_name
            FROM service_order s
            INNER JOIN (SELECT id AS ins_id, name AS insurance_name FROM res_partner) AS i ON (i.ins_id=s.insurance_id)
            INNER JOIN (SELECT id AS par_id, name AS sa_name FROM res_partner) AS p ON (p.par_id=s.service_advisor1)
            WHERE s.register_date >= %s AND s.register_date <= %s AND s.company_id = %s ORDER BY s.state, s.name''')
        params = (data['form']['date_from'], data['form']['date_to'], data['form']['company_id'][0])
        cr.execute(sql, params)

        sa = dict()
        state = dict((fn, dict(zurich=0.0, non_zurich=0.0, pribadi=0.0)) for fn in ['jumlah_unit', 'unit_masuk', 'atur_jadwal', 'order_part'])
        for rec in cr.dictfetchall():
            if not rec['sa_name'] in sa:
                sa[rec['sa_name']] = dict(zurich=0.0, non_zurich=0.0, pribadi=0.0)

            if rec['bill_type'] != 'claim':
                state['jumlah_unit']['pribadi'] += 1
                sa[rec['sa_name']]['pribadi'] += 1

                if rec['status_unit'] == 'new':
                    state['unit_masuk']['pribadi'] += 1
                elif rec['status_unit'] == 'order_part':
                    state['order_part']['pribadi'] += 1
                else:
                    state['atur_jadwal']['pribadi'] += 1
    
            else:
                if rec['insurance_id'] == 3920:
                    state['jumlah_unit']['zurich'] += 1
                    sa[rec['sa_name']]['zurich'] += 1

                    if rec['status_unit'] == 'new':
                        state['unit_masuk']['zurich'] += 1
                    elif rec['status_unit'] == 'order_part':
                        state['order_part']['zurich'] += 1
                    else:
                        state['atur_jadwal']['zurich'] += 1
                else:
                    state['jumlah_unit']['non_zurich'] += 1
                    sa[rec['sa_name']]['non_zurich'] += 1

                    if rec['status_unit'] == 'new':
                        state['unit_masuk']['non_zurich'] += 1
                    elif rec['status_unit'] == 'order_part':
                        state['order_part']['non_zurich'] += 1
                    else:
                        state['atur_jadwal']['non_zurich'] += 1

        res = dict(sa=sa, state=state)
        return res

    @api.model
    def _get_objs_for_report(self, docids, data):
        self.model = self.env.context.get('active_model')
        orders = self._get_orders(data)
        return {
            'doc_ids': docids,
            'doc_model': self.model,
            'form': data['form'],
            'orders': orders,
        }

    def generate_xlsx_report(self, workbook, data, objs):
        sheet = workbook.add_worksheet('report_sa')

        number_normal = workbook.add_format({
            'num_format': '#,##0',
            # 'border': 1
        })
        number_bold = workbook.add_format({
            'num_format': '#,##0',
            'bold': True,
            # 'border': 1
        })
        normal_right = workbook.add_format({
            'align': 'right',
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

        sheet.set_column(0, 0, 4)
        sheet.set_column(1, 1, 45)
        sheet.set_column(2, 6, 12)

        sheet.hide_gridlines(2)
        sheet.write(1, 1, 'Report CSO - %s' % (objs['form']['company_id'][1]), bold_h4)
        sheet.write(2, 1, '%s: %s' % ('Date From', objs['form']['date_from']))
        sheet.write(3, 1, '%s: %s' % ('Date To', objs['form']['date_to']))

        row = 5
        col = 0

        sheet.write(row, col + 1, 'DATA UNIT', bold)
        sheet.write(row, col + 2, 'ZURICH', bold)
        sheet.write(row, col + 3, 'NON ZURICH', bold)
        sheet.write(row, col + 4, 'PRIBADI', bold)

        sheet.write(row + 1, col + 1, 'JUMLAH UNIT')
        sheet.write(row + 2, col + 1, 'UNIT MASUK (W.O)')
        sheet.write(row + 3, col + 1, 'ATUR JADWAL')
        sheet.write(row + 4, col + 1, 'ORDER PART')

        # row += 1
        state_row = row
        for (k, v) in objs['orders']['state'].items():
            if k == 'jumlah_unit':
                state_row = row + 1
            elif k == 'unit_masuk':
                state_row = row + 2
            elif k == 'atur_jadwal':
                state_row = row + 3
            elif k == 'order_part':
                state_row = row + 4

            sheet.write(state_row, col + 2, v['zurich'], number_normal)
            sheet.write(state_row, col + 3, v['non_zurich'], number_normal)
            sheet.write(state_row, col + 4, v['pribadi'], number_normal)

        row += 6
        sheet.write(row, col + 1, 'NAMA SA', bold)
        sheet.write(row, col + 2, 'ZURICH', bold)
        sheet.write(row, col + 3, 'NON ZURICH', bold)
        sheet.write(row, col + 4, 'PRIBADI', bold)

        row += 1
        for (k1, v1) in objs['orders']['sa'].items():
            sheet.write(row, col + 1, k1)
            sheet.write(row, col + 2, v1['zurich'], number_normal)
            sheet.write(row, col + 3, v1['non_zurich'], number_normal)
            sheet.write(row, col + 4, v1['pribadi'], number_normal)
            row += 1
