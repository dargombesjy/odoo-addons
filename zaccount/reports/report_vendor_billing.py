# -*- coding: utf-8 -*-
import datetime
from odoo import models

class ReportVendorBillingXlsx(models.AbstractModel):
    _name = 'report.zaccount.report_vendor_billing_xlsx'
    _description = 'Billing Vendor Service'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, formdata, objs):
        sheet = workbook.add_worksheet('billing')
        number_normal = workbook.add_format({
            'num_format': '#,##0',
            # 'border': 1
        })
        center_normal = workbook.add_format({
            'align': 'center',
            'valign': 'center',
            # 'border': 1
        })
        bottom_normal = workbook.add_format({
            'align': 'center',
            'valign': 'center',
            # 'border': 1
        })
        bold = workbook.add_format({
            'bold': True,
            # 'align': 'right',
            # 'valign': 'center',
            # 'border': 1
        })

        row = 2
        sheet.write(row, 0, 'No.', bold)
        sheet.write(row, 1, 'No. SPK', bold)
        sheet.write(row, 2, 'No. Billing', bold)
        sheet.write(row, 3, 'Vendor', bold)
        sheet.write(row, 4, 'No. Plat', bold)
        sheet.write(row, 5, 'Model', bold)
        sheet.write(row, 6, 'Total Tagihan', bold)

        n = 0
        sum_ = 0
        for line in objs:
            row += 1
            n += 1
            sum_ += line.residual
            sheet.write(row, 0, n)
            sheet.write(row, 1, line.service_id.name)
            sheet.write(row, 2, line.number)
            sheet.write(row, 3, line.partner_id.name)
            sheet.write(row, 4, line.service_id.equipment_id.name)
            sheet.write(row, 5, line.service_id.model)
            sheet.write(row, 6, line.residual, number_normal)
        row += 1
        sheet.write(row, 7, sum_, number_normal)

        row += 2
        sheet.merge_range(row, 6, row, 7, '%s, %s' % ('Bekasi', datetime.date.today()), center_normal)

        row += 1
        sheet.merge_range(row, 0, row, 1, 'Admin Produksi', center_normal)
        sheet.merge_range(row, 2, row, 3, 'Kepala Produksi', center_normal)
        sheet.merge_range(row, 4, row, 5, 'Mengetahui', center_normal)
        sheet.merge_range(row, 6, row, 7, 'Mengetahui', center_normal)

        row += 1
        sheet.merge_range(row, 0, row + 3, 1, '.................', bottom_normal)
        sheet.merge_range(row, 2, row + 3, 3, '.................', bottom_normal)
        sheet.merge_range(row, 4, row + 3, 5, '.................', bottom_normal)
        sheet.merge_range(row, 6, row + 3, 7, '.................', bottom_normal)


