# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class StockMoveWizard(models.TransientModel):
    _name = 'zdg_inventory.stock.move.wizard'

    start_date = fields.Date('Start Date', default=fields.Date.today)
    end_date = fields.Date('End Date', default=fields.Date.today)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    # picking_type = fields.Many2one('stock.picking.type', 'Type', default=1)
    # apply_filter = fields.Boolean('Apply Filter?', default=False)

    @api.multi
    def get_report(self):
        # rec = self.browse(data)
        # data = {}
        # data['form'] = rec.read(['model', 'start_date', 'end_date'])
        # return self.env['report'].get_action(rec, 'zdg_inventory.report_move_xlsx.xlsx',data=data)
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        # if not self.picking_type:
        #     raise UserError(_('Type harus diisi'))
        data['form'] = self.read(['start_date', 'end_date', 'company_id'])[0]   # , 'picking_type', 'apply_filter'])[0]
        # data = {
        #     'start_date': self.start_date,
        #     'end_date': self.end_date,
        #     'picking_type': self.picking_type,
        # }
        return self.with_context(discard_logo_check=True)._print_report(data)
    
    def _print_report(self, data):
        return self.env.ref('zdg_inventory.report_move_xlsx').report_action(self, data=data)