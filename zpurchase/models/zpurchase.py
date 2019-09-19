# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.addons import decimal_precision as dp

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    po_type = fields.Selection([
        ('general', 'PO General'),
        ('service', 'PO Service'),
        ('warehouse', 'PO Inventory')], 'PO Type', default='general')
    items_count = fields.Integer('Items', compute='_count_items')
    service_id = fields.Many2one('service.order', 'Service', copy=False)
    eq_name = fields.Char('License Plate', compute="_compute_equipment", store=True)
#     eq_make = fields.Char('Make', compute="_compute_equipment")
    eq_model = fields.Char('Model', compute="_compute_equipment")
    receiver = fields.Char('Receiver')

    @api.one
    @api.depends('order_line')
    def _count_items(self):
        self.items_count = len(self.order_line)

    @api.one
    @api.depends('service_id')
    def _compute_equipment(self):
        eq = self.service_id.equipment_id
        self.eq_name = eq.name
        details = eq.get_details()
#         self.eq_make = details['make']
        self.eq_model = details['model']

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
