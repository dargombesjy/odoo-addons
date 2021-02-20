import inspect
from odoo import models

class ReportMoveXlsx(models.AbstractModel):
    _name = 'report.zdg_inventory.report_move_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, stock_moves):
        sheet = workbook.add_worksheet('Report')
        header = ['NAMA BARANG', 'PART NUMBER', 'HARGA PRICELIST', 'DISC',
            'HARGA BELI', 'PPN', 'TOTAL', 'NOPOL', 'TGL. TERIMA', 'TGL. AMBIL',
            'PIC', 'AGING', 'LOKASI PART', 'SUPPLIER', 'MEREK', 'TIPE', 'STATUS',
            'LOKASI UNIT', 'KETERANGAN']
        fields = ['product_id.name', 'product_id.default_code', 'product_id.list_price',
            'skip', 'skip', 'skip', 'skip', 'picking_id.eq_name', 'vendor_date',
            'received_date', 'receiver', 'skip', 'skip', 'vendor_id', 'picking_id.eq_make',
            'picking_id.eq_model', 'supply_type', 'skip', 'skip']
        bold = workbook.add_format({'bold': True})
        row = 0
        col = 0
        for h in header:
            sheet.write(row, col, h, bold)
            col += 1
        row += 1
        col = 0
        for obj in stock_moves:
            for field in fields:
                if field == 'skip':
                    continue
                name_ = getattr(obj, field)
                sheet.write(row, col, name_.name)
                col += 1
            row += 1
            col = 0
