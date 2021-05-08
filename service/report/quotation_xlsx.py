# -*- coding: utf-8 -*-
import inspect
from num2words import num2words
from odoo import models, fields
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT

class QuotationXlsx(models.AbstractModel):
    _name = 'report.service.report_quotation_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    
    def generate_xlsx_report(service, workbook, data, services):
        worksheet = workbook.add_worksheet('Quotation')
        number_format = workbook.add_format({
            'num_format': '#,##0',
            'border': 1
        })
        border_format = workbook.add_format({
            'border': 1,
            'valign': 'top'
        })
        header_format_main = workbook.add_format({
            'font_size': 14,
            'bold': True,
            'align': 'center',
            'valign': 'center',
            'border': 1
        })
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'center',
            'border': 1
        })
        header_format_wrap = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'border': 1
        })
        section_format = workbook.add_format({
            'border': 1,
            'bold': True
        })
        center_format = workbook.add_format({
            'align': 'center',
            'valign': 'center',
            'border': 1
        })
        merged_format_top = workbook.add_format({
            'align': 'left',
            'valign': 'top',
            'border': 1
        })
        merged_format_bottom = workbook.add_format({
            'align': 'center',
            'valign': 'bottom',
            'border': 1
        })
        wrap_format = workbook.add_format({
            'text_wrap': True,
            'border': 1
        })
        wrap_format_top = workbook.add_format({
            'text_wrap': True,
            'valign': 'top',
            'border': 1
        })

        worksheet.hide_gridlines(2)
        worksheet.set_column(0, 0, 4)
        worksheet.set_column(1, 1, 12)
        worksheet.set_column(2, 2, 30)
        worksheet.set_column(3, 3, 15)
        worksheet.set_column(4, 4, 5)
        worksheet.set_column(5, 6, 15)

        for service in services:
            # worksheet.merge_range('A1:G1', 'ESTIMASI BIAYA PERBAIKAN KENDARAAN', header_format_main)
            worksheet.merge_range(1, 0, 1, 1, 'No. Estimasi', border_format)
            worksheet.write(1, 2, service.name, border_format)
            worksheet.merge_range(2, 0, 2, 1, 'Asuransi', wrap_format_top)
            worksheet.write(2, 2, service.insurance_id.name or '', wrap_format_top)
            worksheet.set_row(2, 25, None)
            worksheet.merge_range(3, 0, 3, 1, 'Merek Mobil', border_format)
            worksheet.write(3, 2, '%s %s' % (service.make, service.model), border_format)
            worksheet.merge_range(4, 0, 4, 1, 'No. Polisi / Chassis', wrap_format_top)
            worksheet.write(4, 2, '%s / %s' % (service.equipment_id.name, service.chassis_no), wrap_format_top)
            worksheet.set_row(4, 25, None)
            worksheet.merge_range(5, 0, 5, 1, 'Warna', border_format)
            worksheet.write(5, 2, service.base_colour or '', border_format)

            worksheet.merge_range(1, 3, 1, 4, 'Nama Pelanggan', border_format)
            worksheet.merge_range(1, 5, 1, 6, service.partner_id.name, wrap_format)
            worksheet.merge_range(2, 3, 2, 4, 'Alamat', wrap_format_top)
            worksheet.merge_range(2, 5, 2, 6, service.partner_id.street or '', wrap_format_top)
            worksheet.merge_range(3, 3, 3, 4, 'Telepon', border_format)
            worksheet.merge_range(3, 5, 3, 6, service.partner_id.phone or '', border_format)
            worksheet.merge_range(4, 3, 4, 4, 'No. Polis Asuransi', wrap_format_top)
            worksheet.merge_range(4, 5, 4, 6, service.policy_no or '', wrap_format_top)
            worksheet.merge_range(5, 3, 5, 4, 'No. Berkas', border_format)
            worksheet.merge_range(5, 5, 5, 6, service.claim_id or '', border_format)
            # details
            worksheet.write(7, 0, 'No.', header_format_wrap)
            worksheet.merge_range(7, 1, 7, 3, 'KETERANGAN', header_format_wrap)
            worksheet.write(7, 4, 'QTY', header_format_wrap)
            worksheet.write(7, 5, 'HARGA SATUAN \n(Rp.)', header_format_wrap)
            worksheet.write(7, 6, 'TOTAL HARGA \n(Rp.)', header_format_wrap)
            worksheet.set_row(7, 25, None)

            worksheet.merge_range(8, 0, 8, 6, 'PERBAIKAN DAN PENGECATAN', section_format)
            row = 9
            idx = 1
            total_jasa = 0
            for o in service.fees_lines:
                worksheet.write(row, 0, idx, border_format)
                worksheet.write(row, 1, '', border_format)
                worksheet.merge_range(row, 2, row, 3, o.name, border_format)
                worksheet.write(row, 4, o.product_uom_qty, border_format)
                worksheet.write(row, 5, o.price_unit, number_format)
                worksheet.write(row, 6, o.price_subtotal, number_format)
                total_jasa += o.price_subtotal
                row += 1
                idx += 1
            worksheet.merge_range(row, 0, row, 5, 'Total Jasa', section_format)
            worksheet.write(row, 6, total_jasa, number_format)
            row += 1

            worksheet.merge_range(row, 0, row, 6, 'PENGGANTIAN SPAREPART', section_format)
            row += 1
            idx = 1
            total_spareparts = 0
            for r in service.operations:
                if r.approved:
                    worksheet.write(row, 0, idx, border_format)
                    worksheet.write(row, 1, r.part_number, border_format)
                    worksheet.merge_range(row, 2, row, 3, r.name, border_format)
                    worksheet.write(row, 4, r.product_uom_qty, border_format)
                    worksheet.write(row, 5, r.price_unit, number_format)
                    worksheet.write(row, 6, r.price_subtotal, number_format)
                    total_spareparts += r.price_subtotal
                    row += 1
                    idx += 1
            worksheet.merge_range(row, 0, row, 5, 'Total Sparepart', section_format)
            worksheet.write(row, 6, total_spareparts, number_format)

            total = total_spareparts + total_jasa
            row += 1
            worksheet.merge_range(row, 0, row, 5, 'Total', section_format)
            worksheet.write(row, 6, total, number_format)

            row += 1
            worksheet.merge_range(row, 0, row, 1, 'Terbilang:', border_format)
            worksheet.merge_range(row, 2, row, 4, num2words(total, lang='id'), wrap_format_top)
            worksheet.merge_range(row, 5, row, 6, '%s, %s' % ('Bekasi', fields.Date.today()), center_format)

            row += 1
            worksheet.merge_range(row, 0, row + 2, 1, 'Catatan', merged_format_top)
            worksheet.merge_range(row, 2, row + 2, 4, service.quotation_notes or '', wrap_format_top)
            worksheet.merge_range(row, 5, row + 2, 6, service.service_advisor or '', merged_format_bottom)