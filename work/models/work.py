# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

class ServiceOrder(models.Model):
    _inherit = 'service.order'

    received_date = fields.Datetime('Doc. Receive Date')
    sparepart_picking_id = fields.Many2one('stock.picking', 'Sparepart transfer ID', copy=False, index=True)
    consumable_picking_id = fields.Many2one('stock.picking', 'Consumable transfer ID', copy=False, index=True)
    vendor_id = fields.Many2one('res.partner', 'Vendor', copy=False, index=True)
    consumable_lines = fields.One2many(
        'service.consumable', 'service_id', copy=True)
    # readonly=True states={'draft': [('readonly', False)]})

    @api.multi
    def action_create_purchase_fee(self):
        Purchase = self.env['purchase.order']
        Purchase_Line = self.env['purchase.order.line']
        for service in self:
            purchase = Purchase.create({
                'name': service.name,
                'origin': service.name,
                'partner_id': service.vendor_id.id,
                'state': 'draft',
            })

            for fee in service.fees_lines:
                purchase_line = Purchase_Line.create({
                    'order_id': purchase.id,
                    'name': fee.product_id.name,
                    'date_planned': datetime.today(),
                    'product_id': fee.product_id.id,
                    'product_qty': fee.product_uom_qty,
                    'product_uom': fee.product_uom.id,
                    'price_unit': fee.cost_unit,
                    'taxes_id': fee.cost_tax_id,
                })
                fee.write({'purchased': True, 'purchase_line_id': purchase_line.id})
            purchase.button_confirm()
            service.write({'purchased': True, 'purchase_id': purchase.id})

    @api.multi
    def action_create_sparepart_transfer(self):
        # precission = self.env['decimal_precision'].precision_get('Product Unit of Measure')
        Picking = self.env['stock.picking']
        Move_Line = self.env['stock.move']
        partner = self.partner_id
        for service in self:
            if not service.sparepart_picking_id:
                # raise UserError('Sparepart request already created')
                picking = Picking.create({
                    # 'name': '',
                    'service_id': service.id,
                    'origin': service.name,
                    'move_type': 'one',
                    'partner_id': partner.id,
                    'picking_type_id': 2,
                    'location_id': service.location_id,  # 12,
                    'location_dest_id': 9,
                    'state': 'draft',
                })

                for operation in service.operations:
                    Move_Line.create({
                        'name': service.name,
                        'picking_id': picking.id,
                        'product_id': operation.product_id.id,
                        'product_uom_qty': operation.product_uom_qty,
                        'product_uom': operation.product_uom.id,
                        'package_id': False,
                        'package_level_id': False,
                        'location_id': operation.service_id.location_id.id, # 12,  # operation.location_id.id,
                        'location_dest_id': 9,  # operation.location_dest_id.id
                    })
                service.write({'sparepart_picking_id': picking.id})
            return self.env.ref('service.action_work_sparepart_request').report_action(self)

    @api.multi
    def action_create_consumable_transfer(self):
        # precission = self.env['decimal_precision'].precision_get('Product Unit of Measure')
        Picking = self.env['stock.picking']
        Move_Line = self.env['stock.move']
        partner = self.partner_id
        for service in self:
            if not service.consumable_picking_id:
                # raise UserError('Consumable request already created')
                picking = Picking.create({
                    # 'name': '',
                    'service_id': service.id,
                    'origin': service.name,
                    'move_type': 'one',
                    'partner_id': partner.id,
                    'picking_type_id': 2,
                    'location_id': service.location_id, # 12,
                    'location_dest_id': 9,
                    'state': 'draft',
                })

                for other in service.others_lines:
                    Move_Line.create({
                        'name': service.name,
                        'picking_id': picking.id,
                        'product_id': other.product_id.id,
                        'product_uom_qty': other.product_uom_qty,
                        'product_uom': other.product_uom.id,
                        'package_id': False,
                        'package_level_id': False,
                        'location_id': other.service_id.location_id.id, # 12,  # other.location_id.id,
                        'location_dest_id': 9,  # other.location_dest_id.id
                    })

                service.write({'consumable_picking_id': picking.id})
            return self.env.ref('service.action_work_consumable_request').report_action(self)

    @api.one
    def _cost_untaxed(self):
        pass

    @api.one
    def _cost_tax(self):
        pass

    @api.one
    def _cost_total(self):
        pass

    def action_service_ready(self):
        self.mapped('operations').write({'state': 'confirmed'})
        return self.write({'state': 'ready'})

    @api.multi
    def action_service_start(self):
        """ Writes service order state to 'Under Repair'
        @return: True
        """
        if self.filtered(lambda service: service.state not in ['confirmed', 'ready']):
            raise UserError(_("Service must be confirmed before starting repair."))
        self.mapped('operations').write({'state': 'confirmed'})
        return self.write({'state': 'under_repair'})

    @api.multi
    def action_service_end(self):
        if self.filtered(lambda service: service.state != 'under_repair'):
            raise UserError(_("Service must be under repair in order to end."))
        if self.filtered(lambda service: service.work_stage != 'done'):
            raise UserError(_('Stage must "Selesai" to end Service.'))
        for service in self:
            service.write({'repaired': True})
            vals = {'state': 'done'}
            if not service.invoiced and service.invoice_method == 'after_repair':
                vals['state'] = '2binvoiced'
            service.write(vals)
        return True

class ServiceLine(models.Model):
    _inherit = 'service.line'

    @api.one
    def _compute_cost_subtotal(self):
        pass

    @api.onchange('received')
    def onchange_received(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        available_qty_owner = self.env['stock.quant']._get_available_quantity(self.product_id, self.location_id, self.lot_id, owner_id=self.service_id.partner_id, strict=True)
        available_qty_noown = self.env['stock.quant']._get_available_quantity(self.product_id, self.location_id, self.lot_id, strict=True)
        for available_qty in [available_qty_owner, available_qty_noown]:
            if float_compare(available_qty, self.product_uom_qty, precision_digits=precision) >= 0:
                return True
            else:
                return {
                    'name': _('Insufficient Quantity'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'stock.warn.insufficient.qty.service',
                    'view_id': self.env.ref('work.stock_warn_insufficient_qty_form_view').id,
                    'type': 'ir.actions.act_window',
                    'context': {
                        'default_product_id': self.product_id.id,
                        'default_location_id': self.location_id.id,
                        'default_service_id': self.service_id
                    },
                    'target': 'new'
                }

class ServiceFee(models.Model):
    _inherit = 'service.fee'

    @api.one
    def _compute_cost_subtotal(self):
        pass

class ServiceOther(models.Model):
    _inherit = 'service.other'

    @api.one
    def _compute_cost_subtotal(self):
        pass

class ServiceConsumable(models.Model):
    _inherit = 'service.consumable'

    @api.one
    def _compute_cost_subtotal(self):
        pass
