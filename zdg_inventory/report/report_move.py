import inspect
from odoo import models

class ReportMoveXlsx(models.AbstractModel):
    _name = 'report.zdg_inventory.report_move_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, stock_moves):
        sheet = workbook.add_worksheet('Report')
        fields = ['product_id', 'service_id', 'vendor_id']
        row = 0
        col = 0
        for obj in stock_moves:
            # bold = workbook.add_format({'bold': True})
            for field in fields:
                name_ = getattr(obj, field)
                sheet.write(row, col, name_.name)
                col += 1
            row += 1
            col = 0
