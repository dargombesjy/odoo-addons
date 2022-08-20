# -*- coding: utf-8 -*-
import inspect
from datetime import datetime, timedelta
from odoo import api, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT

class ReportMoveXlsx(models.AbstractModel):
    _name = 'report.zdg_inventory.report_move_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    
    @api.model
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
        # move = self.env['stock.move']
        objs = self._get_data(data)
        # if docids:
        #     objs = move.browse(docids)
        #     # ids = docids
        # else:
        #     start = datetime.strptime(data['form']['start_date'], DATE_FORMAT)
        #     end = datetime.strptime(data['form']['end_date'], DATE_FORMAT)
        #     pick_type = data['form']['picking_type'][0]
        #     filtered = data['form']['apply_filter']
        #     # filtered = False
        #     # operation_type = self.env['stock.picking.type'].search([('id', '=', pick_type)], limit=1)
        #     delta = timedelta(days=1)
        #     # delta = (end - start).days + 1
        #     while start <= end:
        #         date = start
        #         start += delta
        #         res = []
        #         ids = move.search([
        #             ('vendor_date', '>=', date.strftime(DATETIME_FORMAT)),
        #             ('vendor_date', '<', start.strftime(DATETIME_FORMAT)),])
        #             # ('picking_type_id', '=', pick_type),])
        #         if filtered:
        #             for move in ids:
        #                 if move.picking_id.picking_type_id.id == pick_type or move.picking_type_id.id == pick_type:
        #                     # ids.remove(move)
        #                     objs.append(move)
        #         else:
        #             objs.extend(ids)
        return objs
        # elif data and 'context' in data:
        #     ids = data["context"].get('active_ids', [])
        # else:
        #     ids = self.env.context.get('active_ids', [])
        # return self.env[self.env.context.get('active_model')].browse(ids)

    def _get_data(self, data):
        cr = self.env.cr

        sql = ('''SELECT p.id, p.name, p.origin, p.date_order, p.po_type, p.service_id, p.eq_name, p.eq_model,
            l.product_id, l.part_no, l.part_name, l.price_unit, l.price_subtotal, l.price_total, l.price_tax,
            l.discount_val, v.vendor_name
            FROM purchase_order p
            LEFT JOIN (SELECT a.product_id, a.order_id, a.price_unit, a.price_subtotal, a.price_total,
                a.price_tax, (a.discount / 100 * a.price_unit * a.product_qty) AS discount_val, b.name AS part_no,
                b.default_code AS part_name
                FROM purchase_order_line a
                LEFT JOIN product_template b ON (a.product_id=b.id)) AS l ON (l.order_id=p.id)
            LEFT JOIN (SELECT id AS vendor_id, name AS vendor_name FROM res_partner) AS v ON (v.vendor_id=p.partner_id)
            WHERE p.po_type = %s AND p.date_order >= %s AND p.date_order <= %s AND p.company_id = %s''')
        params = ('warehouse', data['form']['start_date'], data['form']['end_date'], data['form']['company_id'][0])
        cr.execute(sql, params)
        
        res = []
        for rec in cr.dictfetchall():
            res.append(rec)
        
        return res

    def generate_xlsx_report(self, workbook, data, objs):
        sheet = workbook.add_worksheet('Report')
        format_number = workbook.add_format({
            'num_format': '#,##0'
        })
        # format_date = workbook.add_format({
        #   'num_format': 'dd/mm/yyyy'
        # })
        bold = workbook.add_format({
            'bold': True
        })
        bold_h4 = workbook.add_format({
            'font_size': 14,
            'bold': True,
            'num_format': '#,##0',
            # 'align': 'right',
            # 'valign': 'center',
            'bottom': 1
        })
        
        sheet.set_column(0, 0, 22)

        sheet.write(1, 0, 'REPORT PEMBELIAN PART - %s' % (data['form']['company_id'][1]), bold_h4)
        sheet.write(2, 0, '%s: %s' % ('Date From', data['form']['start_date']))
        sheet.write(3, 0, '%s: %s' % ('Date To', data['form']['end_date']))

        header = ['NAMA BARANG', 'PART NUMBER', 'HARGA PRICELIST', 'DISC',
            'HARGA BELI', 'PPN', 'TOTAL', 'NO. SPK', 'NOPOL', 'TIPE', 'SUPPLIER']

        row = 5
        col = 0
        for h in header:
            sheet.write(row, col, h, bold)
            col += 1
        row += 1
        col = 0
        for obj in objs:
            sheet.write(row, col, obj['part_name'] or '')
            col += 1
            sheet.write(row, col, obj['part_no'] or '')
            col += 1
            sheet.write(row, col, obj['price_unit'] or '', format_number)
            col += 1
            sheet.write(row, col, obj['discount_val'] or '', format_number)
            col += 1
            sheet.write(row, col, obj['price_subtotal'] or '', format_number)
            col += 1
            sheet.write(row, col, obj['price_tax'] or '', format_number)
            col += 1
            sheet.write(row, col, obj['price_total'] or '', format_number)
            col += 1
            sheet.write(row, col, obj['origin'] or '')
            col += 1
            sheet.write(row, col, obj['eq_name'] or '')
            col += 1
            sheet.write(row, col, obj['eq_model'] or '')
            col += 1
            sheet.write(row, col, obj['vendor_name'] or '')

            row += 1
            col = 0
