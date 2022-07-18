from odoo import api, models


class ReportSaXlsx(models.AbstractModel):
    _name = 'report.service.report_sa_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def _get_orders(self, data):
        cr = self.env.cr
        
        sql = ('''SELECT s.name, s.company_id, s.state, s.amount_total, s.invoiced, s.amount_own_risk,
            i.name AS invoice_no, i.amount_untaxed AS invoice_amount, i.amount_tax AS invoice_tax,
            p.name AS insurance
            FROM service_order s LEFT JOIN account_invoice i ON (s.invoice_id=i.id)
            LEFT JOIN res_partner p ON (s.insurance_id=p.id)
            WHERE s.register_date >= %s AND s.register_date <= %s AND s.company_id = %s ORDER BY s.state, s.name''')
        params = (data['form']['date_from'], data['form']['date_to'], data['form']['company_id'][0])
        cr.execute(sql, params)

        state_map = {
            'draft': 1,
            'cancel': 2,
            'confirmed': 3,
            'under_repair': 4,
            'ready': 5,
            '2binvoiced': 6,
            'invoice_except': 7,
            'done': 8,
        }
        result = dict()
        for rec in cr.dictfetchall():
            if not rec['insurance'] in result:
                result[rec['insurance']] = []
            result[rec['insurance']].append(rec)

        final = dict()
        for (k, item) in result.items():
            states = dict()
            for s in ['proses_produksi', 'pending_invoice', 'proses_invoice']:
                st = { 'aggregates': dict((fn, 0.0) for fn in ['jml_spk', 'spk_selesai', 'nominal_invoice', 'nominal_or', 'total_invoice']) }
                states[s] = st
            for row in item:
                inv_amount = 0
                or_amount = 0
                inv_total = 0
                state_num = state_map[row['state']]
                if row['invoiced']:
                    state = 'proses_invoice'
                    inv_amount = row['invoice_amount'] + row['invoice_tax']
                    # inv_total = inv_amount + row['amount_own_risk']
                elif state_num >= 5:
                    state = 'pending_invoice'
                else:
                    state = 'proses_produksi'
                if state != 'proses_produksi':
                    states[state]['aggregates']['spk_selesai'] += 1
                if not row['amount_own_risk'] is None:
                    or_amount = row['amount_own_risk']
                inv_total = inv_amount + or_amount
                
                states[state]['aggregates']['jml_spk'] += 1
                states[state]['aggregates']['nominal_invoice'] += inv_amount
                states[state]['aggregates']['nominal_or'] += or_amount
                states[state]['aggregates']['total_invoice'] += inv_total
            final[k] = states
        return final

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
        sheet.write(1, 1, 'Report SA - %s' % (objs['form']['company_id'][1]), bold_h4)
        sheet.write(2, 1, '%s: %s' % ('Date From', objs['form']['date_from']))
        sheet.write(3, 1, '%s: %s' % ('Date To', objs['form']['date_to']))

        row = 5
        col = 0

        sheet.write(row, col + 1, 'NAMA ASURANSI', bold)
        sheet.write(row, col + 2, 'JUMLAH SPK', bold)
        sheet.write(row, col + 3, 'SPK SELESAI', bold)
        sheet.write(row, col + 4, 'NOMINAL INVOICE', bold)
        sheet.write(row, col + 5, 'NOMINAL OR', bold)
        sheet.write(row, col + 6, 'TOTAL INVOICE', bold)

        row += 1
        for (k, v) in objs['orders'].items():
            row_ins = row
            jml_spk = spk_selesai = nominal_invoice = nominal_or = total_invoice = 0
            
            row += 1
            sheet.write(row, col + 1, 'PROSES PRODUKSI', normal_right)
            sheet.write(row, col + 2, v['proses_produksi']['aggregates']['jml_spk'], number_normal)
            sheet.write(row, col + 3, v['proses_produksi']['aggregates']['spk_selesai'], number_normal)
            sheet.write(row, col + 4, v['proses_produksi']['aggregates']['nominal_invoice'], number_normal)
            sheet.write(row, col + 5, v['proses_produksi']['aggregates']['nominal_or'], number_normal)
            sheet.write(row, col + 6, v['proses_produksi']['aggregates']['total_invoice'], number_normal)
            jml_spk += v['proses_produksi']['aggregates']['jml_spk']
            spk_selesai += v['proses_produksi']['aggregates']['spk_selesai']
            nominal_invoice += v['proses_produksi']['aggregates']['nominal_invoice']
            nominal_or += v['proses_produksi']['aggregates']['nominal_or']
            total_invoice += v['proses_produksi']['aggregates']['total_invoice']

            row += 1
            sheet.write(row, col + 1, 'PENDING INVOICE', normal_right)
            sheet.write(row, col + 2, v['pending_invoice']['aggregates']['jml_spk'], number_normal)
            sheet.write(row, col + 3, v['pending_invoice']['aggregates']['spk_selesai'], number_normal)
            sheet.write(row, col + 4, v['pending_invoice']['aggregates']['nominal_invoice'], number_normal)
            sheet.write(row, col + 5, v['pending_invoice']['aggregates']['nominal_or'], number_normal)
            sheet.write(row, col + 6, v['pending_invoice']['aggregates']['total_invoice'], number_normal)
            jml_spk += v['pending_invoice']['aggregates']['jml_spk']
            spk_selesai += v['pending_invoice']['aggregates']['spk_selesai']
            nominal_invoice += v['pending_invoice']['aggregates']['nominal_invoice']
            nominal_or += v['pending_invoice']['aggregates']['nominal_or']
            total_invoice += v['pending_invoice']['aggregates']['total_invoice']

            row += 1
            sheet.write(row, col + 1, 'PROSES INVOICE', normal_right)
            sheet.write(row, col + 2, v['proses_invoice']['aggregates']['jml_spk'], number_normal)
            sheet.write(row, col + 3, v['proses_invoice']['aggregates']['spk_selesai'], number_normal)
            sheet.write(row, col + 4, v['proses_invoice']['aggregates']['nominal_invoice'], number_normal)
            sheet.write(row, col + 5, v['proses_invoice']['aggregates']['nominal_or'], number_normal)
            sheet.write(row, col + 6, v['proses_invoice']['aggregates']['total_invoice'], number_normal)
            jml_spk += v['proses_invoice']['aggregates']['jml_spk']
            spk_selesai += v['proses_invoice']['aggregates']['spk_selesai']
            nominal_invoice += v['proses_invoice']['aggregates']['nominal_invoice']
            nominal_or += v['proses_invoice']['aggregates']['nominal_or']
            total_invoice += v['proses_invoice']['aggregates']['total_invoice']
            
            sheet.write(row_ins, col + 1, k)
            if k is None:
                sheet.write(row_ins, col + 1, 'PRIBADI')
            sheet.write(row_ins, col + 2, jml_spk, number_normal)
            sheet.write(row_ins, col + 3, spk_selesai, number_normal)
            sheet.write(row_ins, col + 4, nominal_invoice, number_normal)
            sheet.write(row_ins, col + 5, nominal_or, number_normal)
            sheet.write(row_ins, col + 6, total_invoice, number_normal)

            row += 1
            
