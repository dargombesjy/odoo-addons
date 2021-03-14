# -*- coding: utf-8 -*-
import inspect
from datetime import datetime, timedelta
from odoo import models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT

class ReportMoveXlsx(models.AbstractModel):
    _name = 'report.zdg_inventory.report_move_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def _get_objs_for_report(self, docids, data):
        """
        Returns objects for xlx report.  From WebUI these
        are either as docids taken from context.active_ids or
        in the case of wizard are in data.  Manual calls may rely
        on regular context, setting docids, or setting data.

        :param docids: list of integers, typically provided by
            qwebactionmanager for regular Models.
        :param data: dictionary of data, if present typically provided
            by qwebactionmanager for TransientModels.
        :param ids: list of integers, provided by overrides.
        :return: recordset of active model for ids.
        """
        move = self.env['stock.move']
        objs = []
        if docids:
            objs = move.browse(docids)
            # ids = docids
        else:
            start = datetime.strptime(data['form']['start_date'], DATE_FORMAT)
            end = datetime.strptime(data['form']['end_date'], DATE_FORMAT)
            pick_type = data['form']['picking_type'][0]
            filtered = data['form']['apply_filter']
            # filtered = False
            # operation_type = self.env['stock.picking.type'].search([('id', '=', pick_type)], limit=1)
            delta = timedelta(days=1)
            # delta = (end - start).days + 1
            while start <= end:
                date = start
                start += delta
                res = []
                ids = move.search([
                    ('vendor_date', '>=', date.strftime(DATETIME_FORMAT)),
                    ('vendor_date', '<', start.strftime(DATETIME_FORMAT)),])
                    # ('picking_type_id', '=', pick_type),])
                if filtered:
                    for move in ids:
                        if move.picking_id.picking_type_id.id == pick_type or move.picking_type_id.id == pick_type:
                            # ids.remove(move)
                            objs.append(move)
                else:
                    objs.extend(ids)
        return objs
        # elif data and 'context' in data:
        #     ids = data["context"].get('active_ids', [])
        # else:
        #     ids = self.env.context.get('active_ids', [])
        # return self.env[self.env.context.get('active_model')].browse(ids)

    def generate_xlsx_report(self, workbook, data, stock_moves):
        sheet = workbook.add_worksheet('Report')
        format_mumber = workbook.add_format({'num_format': '#,##0'})
        format_date = workbook.add_format({'num_format': 'dd/mm/yyyy'})
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
            sheet.write(row, col, obj.product_id.default_code or '')
            col += 1
            sheet.write(row, col, obj.product_id.name or '')
            col += 1
            sheet.write(row, col, obj.product_id.standard_price or '', format_mumber)
            col += 1
            sheet.write(row, col, '')
            col += 1
            sheet.write(row, col, '')
            col += 1
            sheet.write(row, col, '')
            col += 1
            sheet.write(row, col, '')
            col += 1
            sheet.write(row, col, obj.picking_id.eq_name or '')
            col += 1
            sheet.write(row, col, obj.vendor_date or '', format_date)
            col += 1
            sheet.write(row, col, obj.received_date or '', format_date)
            col += 1
            sheet.write(row, col, obj.receiver or '')
            col += 1
            sheet.write(row, col, '')
            col += 1
            sheet.write(row, col, '')
            col += 1
            sheet.write(row, col, obj.vendor_id.name or '')
            col += 1
            sheet.write(row, col, obj.picking_id.eq_make or '')
            col += 1
            sheet.write(row, col, obj.picking_id.eq_model or '')
            col += 1
            if obj.supply_type == 'vendor':
                sup = 'SUPPLY'
            elif obj.supply_type == 'self':
                sup = 'BELI'
            else:
                sup = ''
            sheet.write(row, col, sup)
            col += 1
            sheet.write(row, col, obj.company_id.display_name or '')
            col += 1
            sheet.write(row, col, obj.picking_type_id.display_name or obj.picking_id.picking_type_id.display_name or '')
            # for field in fields:
            #     if field == 'skip':
            #         continue
            #     name_ = getattr(obj, field)
            #     sheet.write(row, col, name_.name)
            #     col += 1
            row += 1
            col = 0
