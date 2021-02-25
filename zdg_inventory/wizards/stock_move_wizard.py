# -*- coding: utf-8 -*-

from odoo import models, fields, api

class StockMoveWizard(models.TransientModel):
    _name = 'zdg_inventory.stock.move.wizard'

    start_date = fields.Date('Start Date', default=fields.Date.today)
    end_date = fields.Date('End Date', default=fields.Date.today)

    @api.multi
    def get_report(self, cr, context=None):
        # rec = self.browse(data)
        # data = {}
        # data['form'] = rec.read(['model', 'start_date', 'end_date'])
        # return self.env['report'].get_action(rec, 'zdg_inventory.report_move_xlsx.xlsx',data=data)
        
        data = {
            'start_date': self.start_date,
            'end_date': self.end_date
        }
        return self.env.ref('zdg_inventory.report_move_xlsx').report_action(self, data=data)