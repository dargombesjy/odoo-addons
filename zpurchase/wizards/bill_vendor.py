# -*- coding: utf-8 -*-

from odoo import models, fields, api


class BillVendorWizard(models.TransientModel):
    _name = 'zpurchase.bill.vendor.wizard'
    
    @api.multi
    def get_data(self):
        data = {
            'ids': self.ids,
            'model': self._name
        }
        pass
        
    def get_values(self):
        active_ids = self._context.get('active_ids', []) or []
        for record in self.env['purchase.order'].browse(active_ids):
            pass