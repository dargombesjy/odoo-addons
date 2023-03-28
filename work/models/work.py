# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
from passlib.tests.utils import limit


class ServiceOrder(models.Model):
    _inherit = 'service.order'
    _description = 'Production Order'

    sparepart_picking_id = fields.Many2one('stock.picking', 'Sparepart Pick ID',
        readonly=True, copy=False, index=True)
    consumable_picking_id = fields.Many2one('stock.picking', 'Consumable Pick ID',
        readonly=True, copy=False, index=True)
    items_ok = fields.Boolean('Materials received',  compute="_compute_received_flag", store=True)

    @api.one
    @api.depends('operations.received', 'fees_lines.purchased', 'consumable_lines.received')
    def _compute_received_flag(self):
        ops_ng = fees_ng = consumables_ng = False
        if self.operations:
            ops_ng = self.operations.filtered(lambda ops: ops.requested and not ops.received)
            ops_ng = self.operations.filtered(lambda ops: ops.approved and not ops.product_id)
        if self.fees_lines:
            fees_ng = self.fees_lines.filtered(lambda fees: fees.approved and not fees.purchased)
        # others_ok = self.others_lines.filtered(lambda others: others.purchased)
        if self.consumable_lines:
            consumables_ng = self.consumable_lines.filtered(lambda consum: consum.requested and not consum.received)

        if not ops_ng and not fees_ng and not consumables_ng:
            self.items_ok = True

    @api.onchange('vendor_ids')
    def onchange_vendor_ids(self):
        for fee in self.fees_lines:
            fee.vendor_ids = self.vendor_ids

    def create_po_dict(self):
        purchased_vendors = []
        for po in self.purchase_ids:
            purchased_vendors.append(po.partner_id)
        po_vendor = {}
        for fee in self.fees_lines:
            if not fee.approved:  # or fee.cost_unit == 0:
                continue
            for vendor in fee.vendor_ids:
                if fee.purchased:
                    if vendor in purchased_vendors:
                        continue
                if vendor not in po_vendor:
                    po_vendor[vendor] = [fee,]
                else:
                    po_vendor[vendor].append(fee)
                    
            # if not fee.purchased:
            #     for vendor in fee.vendor_ids:
            #         if vendor not in po_vendor:
            #             po_vendor[vendor] = [fee,]
            #         else:
            #             po_vendor[vendor].append(fee)

        if not po_vendor:
            raise UserError(_('All items have been purchased or have not been approved'))
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
                    service.write({'purchase_ids': [(4, purchase.id)]})
                po_ids.append(purchase)
            # service.write({'purchased': True, 'purchase_ids': [(6, 0, [x.id for x in po_ids])]})
            service.write({'purchased': True})

    # @api.multi
    # def action_create_sparepart_transfer(self):
        # # precission = self.env['decimal_precision'].precision_get('Product Unit of Measure')
        # Picking = self.env['stock.picking']
        # Move_Line = self.env['stock.move']
        # partner = self.partner_id
        # for service in self:
            # if not service.operations:
                # raise UserError(_('No Sparepart items to transfer'))
                #
            # outs_all = service.operations.filtered(lambda line: line.approved == True and line.requested == False and line.is_robbing == False)
            # outs_bhn = service.operations.filtered(lambda line: line.approved == True and line.product_id.categ_id == 8 and line.supply_type == 'self')
            #
            # outs = [item for item in outs_all if item not in outs_bhn]
# #             outs = outs_all
            # if not outs:
                # raise UserError(_('No Requested item(s) left to transfer'))
                #
            # if not service.sparepart_picking_id:
                # # raise UserError('Sparepart request already created')
                # picking = Picking.create({
                    # # 'name': '',
                    # 'service_id': service.id,
                    # 'origin': "Part-%s" % service.name,
                    # 'eq_name': service.equipment_id.name,
                    # 'eq_make': service.make,
                    # 'eq_model': service.model,
                    # 'move_type': 'one',
                    # 'partner_id': partner.id,
                    # 'picking_type_id': 2,
                    # 'location_id': service.location_id.id,  # 12,
                    # 'location_dest_id': 9,
                    # 'state': 'draft',
                # })
                # service.write({'sparepart_picking_id': picking.id})
            # else:
                # picking = service.sparepart_picking_id
                #
            # if outs:
                # for operation in outs:
                    # if operation.product_id:
                        # uom_id = operation.product_uom.id
                    # else:
                        # uom_id = 1
                    # moving = Move_Line.create({
                        # 'service_id': service.id,
                        # 'service_line_id': operation.id,
                        # 'name': operation.name,
                        # 'product_category': 'Sparepart',
                        # 'supply_type': operation.supply_type,
                        # 'picking_id': picking.id,
                        # 'picking_type_id': 2,
                        # 'product_id': operation.product_id.id,
                        # 'product_uom_qty': operation.product_uom_qty,
                        # 'product_uom': uom_id, # operation.product_uom.id,
                        # 'package_id': False,
                        # 'package_level_id': False,
                        # 'location_id': operation.service_id.location_id.id, # 12,  # operation.location_id.id,
                        # 'location_dest_id': 9,
                        # 'state': 'draft'
                    # })
                    # operation.write({'move_id': moving.id, 'requested': True})

    @api.multi
    def action_print_sparepart_request(self):
        return self.env.ref('work.action_work_sparepart_request').report_action(self)

    @api.multi
    def action_print_spb(self):
        return self.env.ref('work.action_work_spb').report_action(self)

    @api.multi
    def action_create_consumable_transfer(self):
        # precission = self.env['decimal_precision'].precision_get('Product Unit of Measure')
        Picking = self.env['stock.picking']
        Move_Line = self.env['stock.move']
        partner = self.partner_id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)
        pick = self.env['stock.picking.type'].search([('name', '=', 'Delivery Orders'), ('warehouse_id', '=', warehouse.id)], limit=1)
        for service in self:
            outs_sp = service.operations.filtered(lambda line: line.approved == True and line.product_id.categ_id == 8 and line.supply_type == 'self')
            outs = service.consumable_lines.filtered(lambda line: line.requested == False)

            if not outs_sp and not outs:
                raise UserError(_('No Material items left to transfer'))
#             if not service.consumable_lines:
#                 raise UserError(_('No Consumable items to transfer'))
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
                    # 'picking_type_id': 2,
                    'picking_type_id': pick.id,
                    'location_id': service.location_id.id, # 12,
                    'location_dest_id': 9,
                    'state': 'draft',
                })
                service.write({'consumable_picking_id': picking.id})
            else:
                picking = service.consumable_picking_id

            if outs_sp:
                for bahan_sp in outs_sp:
                    moving = Move_Line.create({
                        'service_id': service.id,
                        'service_line_id': bahan_sp.id,
                        'name': bahan_sp.name,
                        'product_category': 'Bahan',
                        'picking_id': picking.id,
                        # 'picking_type_id': 2,
                        'picking_type_id': pick.id,
                        'product_id': bahan_sp.product_id.id,
                        'product_uom_qty': bahan_sp.product_uom_qty,
                        'product_uom': bahan_sp.product_uom.id,
                        'package_id': False,
                        'package_level_id': False,
                        'location_id': bahan_sp.service_id.location_id.id, # 12,  # other.location_id.id,
                        'location_dest_id': 9,
                        'state': 'draft'
                    })
                    bahan_sp.write({'move_id': moving.id, 'requested': True})

            if outs:
                for bahan in outs:
                    moving = Move_Line.create({
                        'service_id': service.id,
                        'service_line_id': bahan.id,
                        'name': bahan.name,
                        'product_category': 'Consumable',
                        'picking_id': picking.id,
                        # 'picking_type_id': 2,
                        'picking_type_id': pick.id,
                        'product_id': bahan.product_id.id,
                        'product_uom_qty': bahan.product_uom_qty,
                        'product_uom': bahan.product_uom.id,
                        'package_id': False,
                        'package_level_id': False,
                        'location_id': bahan.service_id.location_id.id, # 12,  # other.location_id.id,
                        'location_dest_id': 9,
                        'state': 'draft'
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


# class ServiceEntry(models.Model):
#     _name = 'service.fee.entry'
#     _description = 'Service Entry Sheet'
#     _order = 'create_date_desc'

#     name = fields.Char('Service Entry Sheet')
#     service_fee_id = fields.Many2one('service.fee', 'Service Fee Reference', index=True, ondelete='cascade', required=True)
#     vendor_id = fields.Many2one()

#     @api.multi
#     def action_show_details(self):
#         self.ensure_one()
#         view = self.env.ref('module.record_form_view')
#         return {
#             'name': _('%s') % self.name,
#             'type': 'ir.actions.act_window',
#             'view_type': 'form',
#             'view_model': 'form',
#             'res_model': 'model',
#             'views': [(view.id, 'form')],
#             'view_id': view.id,
#             'target': 'current',
#             'res_id': self.id,
#             'context': dict(self.env.context),
#         }
    