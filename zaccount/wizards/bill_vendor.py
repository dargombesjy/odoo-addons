# -*- coding: utf-8 -*-

from odoo import models, fields, api


class BillVendorWizard(models.TransientModel):
    _name = 'zaccount.bill.vendor.wizard'
    
    @api.multi
    def get_data(self):
        data = {
            'ids': self.ids,
            'model': self._name
        }
        pass
    
    @api.multi    
    def get_values(self):
        active_ids = self._context.get('active_ids', []) or []
    
        data = {
            'ids': active_ids,
            'model': 'account.invoice'
        }
        
        return self.env.ref('zaccount.action_vendor_bill_request').report_action(self, data=data)
        
        
class ReportVendorBillList(models.AbstractModel):
    _name = 'report.zaccount.vendor_bill_request_list'
    
    @api.model
    def _get_report_values(self, docids, data=None):
        ids = []
        if docids:
            ids = docids
        else:
            ids = data['ids']
            
        docs = []
        for record in self.env['account.invoice'].browse(ids):
            record.write({'bill_printed': True})
            docs.append(record)
        
        return {
            'doc_ids': ids,
            'doc_model': 'account.invoice',
            'docs': docs
        }