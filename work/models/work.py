# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

class ServiceOrder(models.Model):
    _inherit = 'service.order'

    # received_date = fields.Datetime('Doc. Receive Date')
    sparepart_picking_id = fields.Many2one('stock.picking', 'Sparepart Pick ID',
        readonly=True, copy=False, index=True)
    consumable_picking_id = fields.Many2one('stock.picking', 'Consumable Pick ID',
        readonly=True, copy=False, index=True)
    # readonly=True states={'draft': [('readonly', False)]})
    items_ok = fields.Boolean('Materials received',  compute="_compute_received_flag", store=True)

    @api.one
    @api.depends('operations.received', 'fees_lines.purchased', 'consumable_lines.received')
    def _compute_received_flag(self):
        ops_ng = fees_ng = consumables_ng = False
        if self.operations:
            ops_ng = self.operations.filtered(lambda ops: not ops.received)
        if self.fees_lines:
            fees_ng = self.fees_lines.filtered(lambda fees: not fees.purchased)
        # others_ok = self.others_lines.filtered(lambda others: others.purchased)
        if self.consumable_lines:
            consumables_ng = self.consumable_lines.filtered(lambda consum: not consum.received)

        if not ops_ng and not fees_ng and not consumables_ng:
            self.items_ok = True

    @api.onchange('vendor_ids')
    def onchange_vendor_ids(self):
        for fee in self.fees_lines:
            fee.vendor_ids = self.vendor_ids

    def create_po_dict(self):
        po_vendor = {}
        for fee in self.fees_lines:
            if not fee.purchased:
                for vendor in fee.vendor_ids:
                    if vendor not in po_vendor:
                        po_vendor[vendor] = [fee,]
                    else:
                        po_vendor[vendor].append(fee)

        if not po_vendor:
            raise UserError(_('All items have been purchased'))
        return po_vendor

    @api.multi
    def action_create_purchase_fee(self):
        Purchase = self.env['purchase.order']
        Purchase_Line = self.env['purchase.order.line']
        po_dict = self.create_po_dict()
        items = list(po_dict.items())
        po_ids = []

        for service in self:
            if self.filtered(lambda service: service.work_stage in ('bongkar', 'ketok')):
                raise UserError(_('At least stage must "Dempul" to create PO.'))
            for item in items:
                purchase = Purchase.create({
                    'po_type': 'service',
                    # 'name': 'Service-%s' % service.name,
                    'origin': service.name,
                    'service_id': service.id,
                    'eq_name': service.equipment_id.name,
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
                        'qty_received': v.product_uom_qty  # all services were received
                    })
                    v.write({'purchased': True, 'purchase_line_id': purchase_line.id})
                po_ids.append(purchase)
            service.write({'purchased': True, 'purchase_ids': [(6, 0, [x.id for x in po_ids])]})

    @api.multi
    def action_create_sparepart_transfer(self):
        # precission = self.env['decimal_precision'].precision_get('Product Unit of Measure')
        Picking = self.env['stock.picking']
        Move_Line = self.env['stock.move']
        partner = self.partner_id
        for service in self:
            if not service.operations:
                raise UserError(_('No Sparepart items to transfer'))
            if not service.sparepart_picking_id:
                # raise UserError('Sparepart request already created')
                picking = Picking.create({
                    # 'name': '',
                    'service_id': service.id,
                    'origin': "Part-%s" % service.name,
                    'eq_name': service.equipment_id.name,
                    'eq_model': service.model,
                    'move_type': 'one',
                    'partner_id': partner.id,
                    'picking_type_id': 2,
                    'location_id': service.location_id.id,  # 12,
                    'location_dest_id': 9,
                    'state': 'draft',
                })
                service.write({'sparepart_picking_id': picking.id})
            else:
                picking = service.sparepart_picking_id

            outs = service.operations.filtered(lambda line: line.requested == False)
            if outs:
                for operation in outs:
                    if operation.product_id:
                        uom_id = operation.product_uom.id
                    else:
                        uom_id = 1
                    moving = Move_Line.create({
                        'service_id': service.id,
                        'service_line_id': operation.id,
                        'name': operation.name,
                        'product_category': 'Sparepart',
                        'supply_type': operation.supply_type,
                        'picking_id': picking.id,
                        'product_id': operation.product_id.id,
                        'product_uom_qty': operation.product_uom_qty,
                        'product_uom': uom_id, # operation.product_uom.id,
                        'package_id': False,
                        'package_level_id': False,
                        'location_id': operation.service_id.location_id.id, # 12,  # operation.location_id.id,
                        'location_dest_id': 9,
                    })
                    operation.write({'move_id': moving.id, 'requested': True})

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
            if not service.consumable_lines:
                raise UserError(_('No Consumable items to transfer'))
            if not service.consumable_picking_id:
                # raise UserError('Consumable request already created')
                picking = Picking.create({
                    # 'name': '',
                    'service_id': service.id,
                    'origin': "Bahan-%s" % service.name,
                    'eq_name': service.equipment_id.name,
                    'eq_model': service.model,
                    'move_type': 'one',
                    'partner_id': partner.id,
                    'picking_type_id': 2,
                    'location_id': service.location_id.id, # 12,
                    'location_dest_id': 9,
                    'state': 'draft',
                })
                service.write({'consumable_picking_id': picking.id})
            else:
                picking = service.consumable_picking_id

            outs = service.consumable_lines.filtered(lambda line: line.requested == False)
            if outs:
                for bahan in outs:
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
                        'location_dest_id': 9,
                    })
                    bahan.write({'move_id': moving.id, 'requested': True})

    @api.multi
    def action_print_consumable_request(self):
        return self.env.ref('work.action_work_consumable_request').report_action(self)

    @api.multi
    def action_service_start(self):
        """ Writes service order state to 'Under Repair'
        @return: True
        """
        if self.filtered(lambda service: service.state not in ['confirmed', 'ready']):
            raise UserError(_("Service must be confirmed before starting repair."))
        self.mapped('operations').write({'state': 'confirmed'})
        return self.write({'state': 'under_repair'})

#     @api.multi
#     def action_service_cancel_draft(self):
#         return self.write({'state': 'draft'})

# class ServiceLine(models.Model):
#     _inherit = 'service.line'

    # @api.one
    # def _compute_cost_subtotal(self):
    #     pass

    # @api.onchange('received')
    # def onchange_received(self):
    #     precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
    #     available_qty_owner = self.env['stock.quant']._get_available_quantity(self.product_id, self.location_id, self.lot_id, owner_id=self.service_id.partner_id, strict=True)
    #     available_qty_noown = self.env['stock.quant']._get_available_quantity(self.product_id, self.location_id, self.lot_id, strict=True)
    #     for available_qty in [available_qty_owner, available_qty_noown]:
    #         if float_compare(available_qty, self.product_uom_qty, precision_digits=precision) >= 0:
    #             return True
    #         else:
    #             return {
    #                 'name': _('Insufficient Quantity'),
    #                 'view_type': 'form',
    #                 'view_mode': 'form',
    #                 'res_model': 'stock.warn.insufficient.qty.service',
    #                 'view_id': self.env.ref('work.stock_warn_insufficient_qty_form_view').id,
    #                 'type': 'ir.actions.act_window',
    #                 'context': {
    #                     'default_product_id': self.product_id.id,
    #                     'default_location_id': self.location_id.id,
    #                     'default_service_id': self.service_id
    #                 },
    #                 'target': 'new'
    #             }

