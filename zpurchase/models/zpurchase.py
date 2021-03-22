# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.addons import decimal_precision as dp

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    _description = 'Purchase Order Customization'

    po_type = fields.Selection([
        ('general', 'PO General'),
        ('service', 'PO Service'),
        ('warehouse', 'PO Inventory'),
        ('entertain', 'PO Entertain')], 'PO Type', required=True, default='general')
    items_count = fields.Integer('Items', compute='_count_items')
    service_id = fields.Many2one('service.order', 'Service', copy=False)
    eq_name = fields.Char('No. Plat')
    eq_model = fields.Char('Model')
    # eq_name = fields.Char('License Plate', compute="_compute_equipment", store=True)
    # eq_model = fields.Char('Model', compute="_compute_equipment")
    receiver = fields.Char('Receiver')

    @api.one
    @api.depends('order_line')
    def _count_items(self):
        self.items_count = len(self.order_line)

    @api.onchange('service_id')
    def onchange_service_id(self):
        eq = self.service_id.equipment_id
        self.eq_name = eq.name
        details = eq.get_details()
        self.eq_model = details['model']
        
    @api.multi
    def action_view_invoice(self):
        '''
        This to override the original function.
        '''
        res = super(PurchaseOrder, self).action_view_invoice()
        res['context']['default_service_id'] = self.service_id.id
        res['context']['default_eq_name'] = self.service_id.equipment_id.name
        res['context']['default_origin_type'] = self.po_type
        return res
        
#     @api.one
#     @api.depends('service_id')
#     def _compute_equipment(self):
#         eq = self.service_id.equipment_id
#         self.eq_name = eq.name
#         details = eq.get_details()
# #         self.eq_make = details['make']
#         self.eq_model = details['model']

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Discount'), default=0.0)

    def _prepare_compute_all_values(self):
        # Hook method to returns the different argument values for the
        # compute_all method, due to the fact that discounts mechanism
        # is not implemented yet on the purchase orders.
        # This method should disappear as soon as this feature is
        # also introduced like in the sales module.
        self.ensure_one()
        return {
            'price_unit': self.price_unit * (1 - (self.discount or 0.0) / 100.0), #add discount
            'currency_id': self.order_id.currency_id,
            'product_qty': self.product_qty,
            'product': self.product_id,
            'partner': self.order_id.partner_id,
        }
