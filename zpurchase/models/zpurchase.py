# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.tools.float_utils import float_compare

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
    picking_id = fields.Many2one('stock.picking', 'Picking', copy=False)
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
    
    def _prepare_po_line_from_move_line(self, line):
        data = {}
        
        return data
    
    @api.onchange('picking_id')
    def picking_change(self):
        if not self.picking_id:
            return {}
        new_lines = self.env['purchase.order.line']
        for line in self.picking_id.move_line - self.order_line.mapped('move_id'):
            data = self._prepare_po_line_from_move_line(line)
            new_line = new_lines.new(data)
            new_lines += new_line

        self.order_line += new_lines
        # self.env.context = dict(self.env.context, from_purchase_order_change=True)
        self.picking_id = False
        return {}


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    
    move_id = fields.Many2one('stock.move', 'Stock Move', copy=False)
    discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Discount'), default=0.0)
    service_id = fields.Integer('Service ID')
    service_line_id = fields.Integer('Service Line ID')

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
    
    @api.multi
    def _prepare_stock_moves(self, picking):
        """ Prepare the stock moves data for one order line. This function returns a list of
        dictionary ready to be used in stock.move's create()
        """
        self.ensure_one()
        res = []
        if self.product_id.type not in ['product', 'consu']:
            return res
        qty = 0.0
        price_unit = self._get_stock_move_price_unit()
        for move in self.move_ids.filtered(lambda x: x.state != 'cancel' and not x.location_dest_id.usage == "supplier"):
            qty += move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom, rounding_method='HALF-UP')
        template = {
            # truncate to 2000 to avoid triggering index limit error
            # TODO: remove index in master?
            'name': (self.name or '')[:2000],
            'product_id': self.product_id.id,
            'product_uom': self.product_uom.id,
            'product_category': self.product_id.categ_id.name,  #added by Suwarno
            'date': self.order_id.date_order,
            'date_expected': self.date_planned,
            'location_id': self.order_id.partner_id.property_stock_supplier.id,
            'location_dest_id': self.order_id._get_destination_location(),
            'picking_id': picking.id,
            'partner_id': self.order_id.dest_address_id.id,
            'move_dest_ids': [(4, x) for x in self.move_dest_ids.ids],
            'state': 'draft',
            'purchase_line_id': self.id,
            'company_id': self.order_id.company_id.id,
            'price_unit': price_unit,
            'picking_type_id': self.order_id.picking_type_id.id,
            'group_id': self.order_id.group_id.id,
            'origin': self.order_id.name,
            'route_ids': self.order_id.picking_type_id.warehouse_id and [(6, 0, [x.id for x in self.order_id.picking_type_id.warehouse_id.route_ids])] or [],
            'warehouse_id': self.order_id.picking_type_id.warehouse_id.id,
        }
        diff_quantity = self.product_qty - qty
        if float_compare(diff_quantity, 0.0,  precision_rounding=self.product_uom.rounding) > 0:
            quant_uom = self.product_id.uom_id
            get_param = self.env['ir.config_parameter'].sudo().get_param
            # Always call '_compute_quantity' to round the diff_quantity. Indeed, the PO quantity
            # is not rounded automatically following the UoM.
            if get_param('stock.propagate_uom') != '1':
                product_qty = self.product_uom._compute_quantity(diff_quantity, quant_uom, rounding_method='HALF-UP')
                template['product_uom'] = quant_uom.id
                template['product_uom_qty'] = product_qty
            else:
                template['product_uom_qty'] = self.product_uom._compute_quantity(diff_quantity, self.product_uom, rounding_method='HALF-UP')
            res.append(template)
        return res
