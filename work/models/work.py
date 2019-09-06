# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

class ServiceOrder(models.Model):
    _inherit = 'service.order'

    # received_date = fields.Datetime('Doc. Receive Date')
    sparepart_picking_id = fields.Many2one('stock.picking', 'Sparepart Pick ID', copy=False, index=True)
    consumable_picking_id = fields.Many2one('stock.picking', 'Consumable Pick ID', copy=False, index=True)
    consumable_lines = fields.One2many(
        'service.consumable', 'service_id', copy=True)
    # readonly=True states={'draft': [('readonly', False)]})
    items_ok = fields.Boolean('Materials received',  compute="_compute_received_flag", store=True)

    @api.one
    @api.depends('operations', 'fees_lines', 'consumable_lines')
    # @api.depends('operations', 'fees_lines', 'others_lines', 'consumable_lines')
    def _compute_received_flag(self):
        ops_ok = self.operations.filtered(lambda ops: ops.received)
        fees_ok = self.fees_lines.filtered(lambda fees: fees.purchased)
        # others_ok = self.others_lines.filtered(lambda others: others.purchased)
        consumables_ok = self.consumable_lines.filtered(lambda consum: consum.received)
        if ops_ok and fees_ok and consumables_ok:
            self.items_ok = True

    def create_po_dict(self):
        po_vendor = {}
        po_items = []
        for fee in self.fees_lines:
            for vendor in fee.vendor_ids:
                if vendor not in po_vendor:
                    po_vendor[vendor] = po_items.append(fee)
        return po_vendor

    @api.multi
    def action_create_purchase_fee(self):
        Purchase = self.env['purchase.order']
        Purchase_Line = self.env['purchase.order.line']
        po_dict = self.create_po_dict()
        items = list(po_dict.items())

        for service in self:
            # for fee in service.fees_lines:
            for item in items:
                purchase = Purchase.create({
                    'name': 'PO Service-"%s"' % service.name,
                    'origin': service.name,
                    'partner_id': item[0].id,
                    'state': 'draft',
                })
                for v in item[1]:
                    purchase_line = Purchase_Line.create({
                        'order_id': purchase.id,
                        'name': v.product_id.name,
                        'date_planned': datetime.today(),
                        'product_id': v.product_id.id,
                        'product_qty': v.product_uom_qty,
                        'product_uom': v.product_uom.id,
                        'price_unit': v.cost_unit,
                    })
            # fee.write({'purchased': True, 'purchase_line_id': purchase_line.id})
        service.write({'purchased': True})

    # @api.multi
    # def action_create_purchase_fee(self):
    #     Purchase = self.env['purchase.order']
    #     Purchase_Line = self.env['purchase.order.line']
    #     for service in self:
    #         purchase = Purchase.create({
    #             'name': service.name,
    #             'origin': service.name,
    #             'partner_id': service.vendor_id.id,
    #             'state': 'draft',
    #         })
    #
    #         for fee in service.fees_lines:
    #             # if fee.cost_unit == 0:
    #             #     raise UserError(_('Cost not updated'))
    #             purchase_line = Purchase_Line.create({
    #                 'order_id': purchase.id,
    #                 'name': fee.product_id.name,
    #                 'date_planned': datetime.today(),
    #                 'product_id': fee.product_id.id,
    #                 'product_qty': fee.product_uom_qty,
    #                 'product_uom': fee.product_uom.id,
    #                 'price_unit': fee.cost_unit,
    #                 # 'taxes_id': fee.cost_tax_id,
    #             })
    #             fee.write({'purchased': True, 'purchase_line_id': purchase_line.id})
    #         # purchase.button_confirm()
    #         service.write({'purchased': True, 'purchase_id': purchase.id})

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
                    # 'origin': service.name,
                    'eq_name': service.equipment_id.name,
                    'eq_model': service.model,
                    'move_type': 'one',
                    'partner_id': partner.id,
                    'picking_type_id': 2,
                    'location_id': service.location_id.id,  # 12,
                    'location_dest_id': 9,
                    'state': 'draft',
                })

                for operation in service.operations:
                    if operation.product_id:
                        uom_id = operation.product_uom.id
                    else:
                        uom_id = 1
                    moving = Move_Line.create({
                        'service_id': service.id,
                        'service_line_id': operation.id,
                        'name': operation.name,
                        'product_category': 'Sparepart',
                        'picking_id': picking.id,
                        'product_id': operation.product_id.id,
                        'product_uom_qty': operation.product_uom_qty,
                        'product_uom': uom_id, # operation.product_uom.id,
                        'package_id': False,
                        'package_level_id': False,
                        'location_id': operation.service_id.location_id.id, # 12,  # operation.location_id.id,
                        'location_dest_id': 9,  # operation.location_dest_id.id
                        # 'move_line_ids': [(0, 0, {'product_id': operation.product_id.id,
                        #                        'picking_id': picking.id,
                        #                        # 'lot_id': operation.lot_id.id,
                        #                        'product_uom_qty': 0,  # bypass reservation here
                        #                        'product_uom_id': operation.product_uom.id,
                        #                        # 'qty_done': operation.product_uom_qty,
                        #                        'package_id': False,
                        #                        'result_package_id': False,
                        #                        # 'owner_id': owner_id,
                        #                        'location_id': operation.service_id.location_id.id, #TODO: owner stuff
                        #                        'location_dest_id': 9, # operation.location_dest_id.id,
                        #                        'service_line_id': operation.id,
                        #                        'product_alias': operation.name,})],
                    })
                    operation.write({'move_id': moving.id, 'received': True})
                service.write({'sparepart_picking_id': picking.id})

    @api.multi
    def action_print_sparepart_request(self):
        return self.env.ref('work.action_work_sparepart_request').report_action(self)

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
                    # 'origin': service.name,
                    'eq_name': service.equipment_id.name,
                    'eq_model': service.model,
                    'move_type': 'one',
                    'partner_id': partner.id,
                    'picking_type_id': 2,
                    'location_id': service.location_id.id, # 12,
                    'location_dest_id': 9,
                    'state': 'draft',
                })

                for bahan in service.consumable_lines:
                    moving = Move_Line.create({
                        'service_id': service.id,
                        'service_line_id': bahan.id,
                        'name': bahan.name,
                        'product_category': 'Consumable',
                        'picking_id': picking.id,
                        'product_id': bahan.product_id.id,
                        'product_uom_qty': bahan.product_uom_qty,
                        'product_uom': bahan.product_uom.id,
                        'package_id': False,
                        'package_level_id': False,
                        'location_id': bahan.service_id.location_id.id, # 12,  # other.location_id.id,
                        'location_dest_id': 9,  # other.location_dest_id.id
                        # 'move_line_ids': [(0, 0, {'product_id': bahan.product_id.id,
                        #                        'picking_id': picking.id,
                        #                        # 'lot_id': bahan.lot_id.id,
                        #                        'product_uom_qty': 0,  # bypass reservation here
                        #                        'product_uom_id': bahan.product_uom.id,
                        #                        # 'qty_done': bahan.product_uom_qty,
                        #                        'package_id': False,
                        #                        'result_package_id': False,
                        #                        # 'owner_id': owner_id,
                        #                        'location_id': bahan.service_id.location_id.id, #TODO: owner stuff
                        #                        'location_dest_id': 9, # bahan.location_dest_id.id,
                        #                        'service_line_id': bahan.id,
                        #                        'product_alias': bahan.name,})],
                    })
                    bahan.write({'move_id': moving.id, 'received': True})
                service.write({'consumable_picking_id': picking.id})

    @api.multi
    def action_print_consumable_request(self):
        return self.env.ref('work.action_work_consumable_request').report_action(self)

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
        if self.filtered(lambda service: service.work_stage != 'delivered'):
            raise UserError(_('Stage must "Delivered" to end Service.'))
        if self.filtered(lambda service: service.items_ok == False):
            raise UserError(_('All items must received or purchased'))
        for service in self:
            service.write({'repaired': True})
            vals = {'state': 'done'}
            if not service.invoiced and service.invoice_method == 'after_repair':
                vals['state'] = '2binvoiced'
            service.write(vals)
        return True

    @api.multi
    def action_service_cancel_draft(self):
        return self.write({'state': 'draft'})

class ServiceLine(models.Model):
    _inherit = 'service.line'

    # @api.one
    # def _compute_cost_subtotal(self):
    #     pass

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

#     @api.one
#     def _compute_cost_subtotal(self):
#         pass
#
class ServiceOther(models.Model):
    _inherit = 'service.other'

#     @api.one
#     def _compute_cost_subtotal(self):
#         pass
#
class ServiceConsumable(models.Model):
    _inherit = 'service.consumable'

#     @api.one
#     def _compute_cost_subtotal(self):
#         pass
