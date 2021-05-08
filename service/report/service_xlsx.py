# -*- coding: utf-8 -*-
import inspect
from num2words import num2words
from odoo import models, fields
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT

class FormServiceXlsx(models.AbstractModel):
    _name = 'report.service.form_service_xlsx'
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
        worksheet.set_column(1, 1, 16)
        worksheet.set_column(2, 2, 30)
        worksheet.set_column(3, 3, 15)
        worksheet.set_column(4, 4, 5)
        worksheet.set_column(5, 8, 15)

        row = 1
        for service in services:
            # worksheet.merge_range('A1:G1', 'ESTIMASI BIAYA PERBAIKAN KENDARAAN', header_format_main)
            worksheet.merge_range(row, 0, row, 1, 'No. Estimasi', border_format)
            worksheet.merge_range(row, 2, row, 3, service.name, border_format)
            worksheet.merge_range(row, 4, row, 5, 'Nama Pelanggan', border_format)
            worksheet.merge_range(row, 6, row, 8, service.partner_id.name, wrap_format)
            row += 1
            worksheet.merge_range(row, 0, row, 1, 'Asuransi', wrap_format_top)
            worksheet.merge_range(row, 2, row, 3, service.insurance_id.name or '', wrap_format_top)
            worksheet.merge_range(row, 4, row, 5, 'Alamat', wrap_format_top)
            worksheet.merge_range(row, 6, row, 8, service.partner_id.street or '', wrap_format_top)
            worksheet.set_row(row, 25, None)
            row += 1
            worksheet.merge_range(row, 0, row, 1, 'Merek Mobil', border_format)
            worksheet.merge_range(row, 2, row, 3, '%s %s' % (service.make, service.model), border_format)
            worksheet.merge_range(row, 4, row, 5, 'Telepon', border_format)
            worksheet.merge_range(row, 6, row, 8, service.partner_id.phone or '', border_format)
            row += 1
            worksheet.merge_range(row, 0, row, 1, 'No. Polisi / Chassis', wrap_format_top)
            worksheet.merge_range(row, 2, row, 3, '%s / %s' % (service.equipment_id.name, service.chassis_no), wrap_format_top)
            worksheet.merge_range(row, 4, row, 5, 'No. Polis Asuransi', wrap_format_top)
            worksheet.merge_range(row, 6, row, 8, service.policy_no or '', wrap_format_top)
            # worksheet.set_row(row, 25, None)
            row += 1
            worksheet.merge_range(row, 0, row, 1, 'Warna', border_format)
            worksheet.merge_range(row, 2, row, 3, service.base_colour or '', border_format)
            worksheet.merge_range(row, 4, row, 5, 'No. Berkas', border_format)
            worksheet.merge_range(row, 6, row, 8, service.claim_id or '', border_format)
            
            # details
            row += 1
            worksheet.write(row, 0, 'No.', header_format_wrap)
            worksheet.merge_range(row, 1, row, 3, 'KETERANGAN', header_format_wrap)
            worksheet.write(row, 4, 'QTY', header_format_wrap)
            worksheet.write(row, 5, 'HARGA SATUAN \n(Rp.)', header_format_wrap)
            worksheet.write(row, 6, 'TOTAL HARGA \n(Rp.)', header_format_wrap)
            worksheet.write(row, 7, 'TOTAL COST \n(Rp.)', header_format_wrap)
            worksheet.write(row, 8, 'GAIN / LOST \n(Rp.)', header_format_wrap)
            worksheet.set_row(row, 26, None)
            row += 1
            worksheet.merge_range(row, 0, row, 8, 'PERBAIKAN DAN PENGECATAN', section_format)
            
            row += 1
            idx = 1
            total_jasa = 0
            for o in service.fees_lines:
                worksheet.write(row, 0, idx, border_format)
                worksheet.write(row, 1, '', border_format)
                worksheet.merge_range(row, 2, row, 3, o.name, border_format)
                worksheet.write(row, 4, o.product_uom_qty, border_format)
                worksheet.write(row, 5, o.price_unit, number_format)
                worksheet.write(row, 6, o.price_subtotal, number_format)
                worksheet.write(row, 7, 0, number_format)
                worksheet.write(row, 8, 0, number_format)
                total_jasa += o.price_subtotal
                row += 1
                idx += 1
            worksheet.merge_range(row, 0, row, 5, 'Total Jasa', section_format)
            worksheet.write(row, 6, total_jasa, number_format)
            worksheet.write(row, 7, service.cost_fees, number_format)
            worksheet.write(row, 8, total_jasa - service.cost_fees, number_format)
            row += 1

            worksheet.merge_range(row, 0, row, 8, 'PENGGANTIAN SPAREPART', section_format)
            row += 1
            idx = 1
            total_spareparts = 0
            total_cost_part = 0
            for r in service.operations:
                if r.approved:
                    worksheet.write(row, 0, idx, border_format)
                    worksheet.write(row, 1, r.product_id.name, border_format)
                    worksheet.merge_range(row, 2, row, 3, r.name, border_format)
                    worksheet.write(row, 4, r.product_uom_qty, border_format)
                    worksheet.write(row, 5, r.price_unit, number_format)
                    worksheet.write(row, 6, r.price_subtotal, number_format)
                    worksheet.write(row, 7, r.cost_subtotal, number_format)
                    worksheet.write(row, 8, r.price_subtotal - r.cost_subtotal, number_format)
                    total_spareparts += r.price_subtotal
                    total_cost_part += r.cost_subtotal
                    row += 1
                    idx += 1
            worksheet.merge_range(row, 0, row, 5, 'Total Sparepart', section_format)
            worksheet.write(row, 6, total_spareparts, number_format)
            worksheet.write(row, 7, service.cost_operations, number_format)
            worksheet.write(row, 8, total_spareparts - service.cost_operations, number_format)

            total = total_spareparts + total_jasa
            total_cost = service.cost_operations + service.cost_fees
            row += 1
            worksheet.merge_range(row, 0, row, 5, 'Total', section_format)
            worksheet.write(row, 6, total, number_format)
            worksheet.write(row, 7, total_cost, number_format)
            worksheet.write(row, 8, total - total_cost, number_format)

            # row += 1
            # worksheet.merge_range(row, 0, row, 1, 'Terbilang:', border_format)
            # worksheet.merge_range(row, 2, row, 4, num2words(total, lang='id'), wrap_format_top)
            # worksheet.merge_range(row, 5, row, 6, '%s, %s' % ('Bekasi', fields.Date.today()), center_format)

            # row += 1
            # worksheet.merge_range(row, 0, row + 2, 1, 'Catatan', merged_format_top)
            # worksheet.merge_range(row, 2, row + 2, 4, service.quotation_notes or '', wrap_format_top)
            # worksheet.merge_range(row, 5, row + 2, 6, service.service_advisor or '', merged_format_bottom)
            row += 3