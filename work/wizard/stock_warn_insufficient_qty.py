# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class StockWarnInsufficientQtyService(models.TransientModel):
    _name = 'stock.warn.insufficient.qty.service'
    _inherit = 'stock.warn.insufficient.qty'
    _description = 'Warn Insufficient Repair Quantity'

    service_id = fields.Many2one('service.order', string='Service')

    def action_done(self):
        pass
        # self.ensure_one()
        # return self.service_id.action_repair_confirm()
