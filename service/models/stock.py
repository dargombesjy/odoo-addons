# -*- coding: utf-8 -*-
# from datetime import datetime
# from dateutil import relativedelta
from itertools import groupby
from operator import itemgetter

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from .service import SUPPLY_TYPES
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_round, float_is_zero

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    service_id = fields.Many2one('service.order')
    eq_name = fields.Char('License Plate')
    eq_make = fields.Char('Make')
    eq_model = fields.Char('Model')
    receiver = fields.Char('Receiver')
    received_date = fields.Date('Received Date')
    vendor_id = fields.Many2one(
        'res.partner', 'Vendor', index=True, readonly=True,
        states={'draft': [('readonly', False)]})
    is_sparepart = fields.Boolean('Is Sparepart', compute='_compute_ispart')
    po_created = fields.Boolean('PO Created')
    purchase_ids = fields.Many2many('purchase.order', 'picking_po',
        'picking_id', 'purchase_order_id', 'Purchase Orders')

    @api.one
    @api.depends('picking_type_id')
    def _compute_vendor_detail(self):  
        pass
    
    @api.one
    @api.depends('origin')
    def _compute_ispart(self):
        self.is_sparepart = True
        if self.origin:
            self.is_sparepart = 'Part-' in self.origin
        # self.is_sparepart = 'Part-' in self.origin

    @api.multi
    def action_confirm(self):
        if self.mapped('move_lines').filtered(lambda move: not move.product_id):
            raise UserError(_('All items must have Product ID'))

        self.mapped('package_level_ids').filtered(lambda pl: pl.state == 'draft' and not pl.move_ids)._generate_moves()
        # call `_action_confirm` on every draft move
        self.mapped('move_lines')\
            .filtered(lambda move: move.state == 'draft')\
            ._action_confirm()
        # call `_action_assign` on every confirmed move which location_id bypasses the reservation
        self.filtered(lambda picking: picking.location_id.usage in ('supplier', 'inventory', 'production') and picking.state == 'confirmed')\
            .mapped('move_lines')._action_assign()
        return True

    @api.multi
    def action_assign(self):
        """ Check availability of picking moves.
        This has the effect of changing the state and reserve quants on available moves, and may
        also impact the state of the picking as it is computed based on move's states.
        @return: True
        """
        material_out = self.picking_type_id.name == 'Pick' or self.picking_type_id.name == 'Delivery Orders'
        # if self.picking_type_id.name == 'Pick' or self.picking_type_id.name == 'Delivery Orders':
        if material_out:
            not_valid = self.mapped('move_lines').filtered(lambda move: move.product_category == 'Sparepart' and (move.vendor_qty == 0 or not move.vendor_date))
            if not_valid:
                raise UserError(_('Qty. Terima dan Tgl. Terima harus diisi'))
            
            to_receive = self.mapped('move_lines')\
                .filtered(lambda move:move.supply_type == 'vendor' and move.product_category == 'Sparepart'\
                and move.vendor_id and move.vendor_qty > 0 and move.vendor_date and not move.auto_receipt_id)
            
            # hanya auto receive jika ada config parameter allow_auto_receipt
            allow_auto_receipt = self.env['ir.config_parameter'].sudo().get_param('service.allow_auto_receipt')
            if to_receive and allow_auto_receipt == 'True':
                self.action_create_supply_receipt(to_receive)

        self.filtered(lambda picking: picking.state == 'draft').action_confirm()
        moves = self.mapped('move_lines').filtered(lambda move: move.state not in ('draft', 'cancel', 'done'))
        if not moves:
            raise UserError(_('Nothing to check the availability for.'))
        # If a package level is done when confirmed its location can be different than where it will be reserved.
        # So we remove the move lines created when confirmed to set quantity done to the new reserved ones.
        package_level_done = self.mapped('package_level_ids').filtered(lambda pl: pl.is_done and pl.state == 'confirmed')
        package_level_done.write({'is_done': False})
        moves._action_assign()
        package_level_done.write({'is_done': True})
        
        if material_out:
            if self.mapped('move_lines').filtered(lambda move:move.supply_type == 'self' and move.product_category == 'Sparepart'):
                self.service_id.action_set_part_cost()
        return True

    def _create_transfer_dict(self, move_lines):
        receipt_vendor = {}
        for move in move_lines:
            if move.supply_type != 'vendor' or move.product_category != 'Sparepart':
                continue
            if move.vendor_id not in receipt_vendor:
                receipt_vendor[move.vendor_id] = [move,]
            else:
                receipt_vendor[move.vendor_id].append(move)
        if not receipt_vendor:
            raise UserError(_('Tidak ada Part Vendor Supply'))
        return receipt_vendor
    
    def action_create_supply_receipt(self, move_lines):
        """ Create automatic receipt for sparepart supplied by vendor
        @return: True
        """
        Picking = self.env['stock.picking']
        move_supply = self.env['stock.move']
        
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.service_id.company_id.id)], limit=1)
        pick = self.env['stock.picking.type'].search([('name', '=', 'Receipts'), ('warehouse_id', '=', warehouse.id)], limit=1)
        source = self.env['stock.location'].search([('name', '=', 'Vendors')], limit=1)
        destination = pick.default_location_dest_id
        
        transfer_dict = self._create_transfer_dict(move_lines)
        transfer_items = list(transfer_dict.items())

        for item in transfer_items:
            picking = Picking.create({
                        # 'name': '',
                        'service_id': self.service_id.id,
                        'origin': 'receipt_4: %s' % (self.name),
                        'eq_name': self.eq_name,
                        'eq_make': self.eq_make,
                        'eq_model': self.eq_model,
                        'move_type': 'one',
                        'partner_id': item[0].id,
                        'picking_type_id': pick.id,
                        'location_id': source.id,
                        'location_dest_id': self.location_id.id,
                        'state': 'draft',
                    })
            # if self.picking_type_id.name == 'Pick':
            
            for move in item[1]:
            # for move in move_lines:
                # if move.product_category == 'Sparepart' and move.vendor_id and move.vendor_qty > 0:
                # if move.product_category == 'Sparepart' and move.vendor_id and move.vendor_qty > 0\
                    # and move.supply_type == 'vendor' and not move.auto_receipt_id:
                        
                total_received = move.vendor_received + move.vendor_qty
                move_qty = 0
                if total_received <= move.product_uom_qty:
                    move_qty = move.vendor_qty
                else:
                    if move.vendor_received < move.product_uom_qty:
                        move_qty = move.product_uom_qty - move.vendor_received
                        total_received = move.product_uom_qty
        
                if move_qty > 0:
                    supply = move_supply.create({
                        # 'name': 'receipt_4: %s' % (move.name),
                        'name': 'receipt_4: %s-%s' % (move.picking_id.name, move.name),
                        'date': move.vendor_date,
                        'product_id': move.product_id.id,
                        'product_uom_qty': move.product_uom_qty,
                        'product_uom': move.product_uom.id,
                        'product_category': move.product_category,
                        'supply_type': 'vendor',
                        # 'partner_id': move.picking_id.partner_id.id,
                        'partner_id': move.vendor_id.id,
                        'picking_type_id': pick.id,
                        'picking_id': picking.id,
                        'location_id': source.id,
                        'location_dest_id': move.location_id.id,
                        'move_line_ids': [(0, 0, {'product_id': move.product_id.id,
                                                #'lot_id': move.lot_id,
                                                'product_uom_qty': move.product_uom_qty,  # bypass reservation here
                                                'product_uom_id': move.product_uom.id,
                                                'qty_done': move_qty,
                                                'package_id': False,
                                                'result_package_id': False,
                                                #'owner_id': #owner_id,
                                                'location_id': source.id, #TODO: owner stuff
                                                'location_dest_id': move.location_id.id })], #operation.location_dest_id.id,})],
                        'origin': move.id,
                        'service_id': move.service_id.id,
                        'service_line_id': move.service_line_id,
                    })
                    move.write({
                        'vendor_received': total_received,
                        'auto_receipt_id': supply.id
                    })
                    # supply._action_done()
            picking.action_done()
        return True
    
    def _create_po_dict(self):
        po_vendor = {}
        for move in self.move_lines:
            if move.supply_type != 'self' or move.product_category != 'Sparepart':
                continue
            if move.vendor_id not in po_vendor:
                po_vendor[move.vendor_id] = [move,]
            else:
                po_vendor[move.vendor_id].append(move)
        if not po_vendor:
            raise UserError(_('Tidak ada Part Self Supply'))
        return po_vendor
    
    @api.multi
    def action_create_purchase(self):
        Purchase = self.env['purchase.order']
        Purchase_Line = self.env['purchase.order.line']
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.service_id.company_id.id)], limit=1)
        pick_type = self.env['stock.picking.type'].search([('name', '=', 'Receipts'), ('warehouse_id', '=', warehouse.id)], limit=1)

        for pick in self:
            if pick.purchase_ids:
                raise UserError(_('PO sudah dibuat'))
            po_dict = pick._create_po_dict()
            items = list(po_dict.items())
            po_ids = []
            for item in items:
                purchase = Purchase.create({
                    'po_type': 'warehouse',
                    'origin': 'Part-%s.' % (pick.service_id.name),
                    # 'service_id': pick.service_id.id,
                    'eq_name': pick.eq_name,
                    'eq_model': pick.eq_model,
                    'partner_id': item[0].id,
                    'picking_type_id': pick_type.id,
                    'state': 'draft',
                })
                for v in item[1]:
                    purchase_line = Purchase_Line.create({
                        'order_id': purchase.id,
                        'name': v.product_id.name,
                        'date_planned': fields.Date.today(),
                        'product_id': v.product_id.id,
                        'product_qty': v.product_uom_qty,
                        'product_uom': v.product_uom.id,
                        'price_unit': v.product_id.standard_price,
                        # 'qty_received': v.product_uom_qty
                    })
                    # v.write({'purchase_line_id': purchase_line.id})
                pick.write({'purchase_ids': [(4, purchase.id)]})
                # po_ids.append(purchase)
            # pick.write({'po_created': True, 'purchase_ids': [(6, 0, [x.id for x in po_ids])]})
            pick.write({'po_created': True})

        # action = self.env.ref('purchase.purchase_order_form')
        # result = action.read()[0]
        #
        # result['context'] = {
            # }
        # return result
    
    # @api.multi
    # def action_view_po(self):
        # self.ensure_one()
        # view = self.env.ref('stock.stock_scrap_form_view2')
        # products = self.env['product.product']
        # for move in self.move_lines:
            # if move.state not in ('draft', 'cancel') and move.product_id.type in ('product', 'consu'):
                # products |= move.product_id
        # return {
            # 'name': _('Scrap'),
            # 'view_type': 'form',
            # 'view_mode': 'form',
            # 'res_model': 'stock.scrap',
            # 'view_id': view.id,
            # 'views': [(view.id, 'form')],
            # 'type': 'ir.actions.act_window',
            # 'context': {'default_picking_id': self.id, 'product_ids': products.ids},
            # 'target': 'new',
        # }

class StockMove(models.Model):
    _inherit = 'stock.move'

    service_id = fields.Many2one('service.order')
    service_line_id = fields.Integer('Line Id')
    product_id = fields.Many2one(
        'product.product', 'Product',
        domain=[('type', 'in', ['product', 'consu'])], index=True, required=False)
    product_category = fields.Char('Product Category')
    supply_type = fields.Selection(SUPPLY_TYPES, 'Supply Type')
    part_number = fields.Char('Kode Part Admin', compute='_compute_part_admin')
    vendor_id = fields.Many2one('res.partner', 'Vendor', index=True)
    vendor_qty = fields.Float('Qty. Terima')
    vendor_date = fields.Date('Tgl. Terima')
    vendor_received = fields.Float('Recv')
    receiver = fields.Char('Penerima')
    received_date = fields.Date('Tgl. Ambil')
    auto_receipt_id = fields.Many2one('stock.move', 'Receipt', copy=False)
    delete_flag = fields.Boolean('Deleted', default=False)
    
    @api.one
    @api.depends('service_line_id')
    def _compute_part_admin(self):
        service_line = self.env['service.line'].search([('id', '=', self.service_line_id)], limit=1)
        self.part_number = service_line.part_number
    
    def action_set_draft(self):
        return self.write({'state': 'draft'})

    @api.constrains('product_uom')
    def _check_uom(self):
        moves_error = self.filtered(lambda move: move.product_id.uom_id.category_id != move.product_uom.category_id)
        sparepart = self.filtered(lambda move: move.product_category == 'Sparepart')
        if sparepart:
            moves_error = False
        # if self.product_category == 'Sparepart' and self.state == 'draft':
        #     moves_error = False
        if moves_error:
            user_warning = _('You cannot perform the move because the unit of measure has a different category as the product unit of measure.')
            for move in moves_error:
                user_warning += _('\n\n%s --> Product UoM is %s (%s) - Move UoM is %s (%s)') % (move.product_id.display_name, move.product_id.uom_id.name, move.product_id.uom_id.category_id.name, move.product_uom.name, move.product_uom.category_id.name)
            user_warning += _('\n\nBlocking: %s') % ' ,'.join(moves_error.mapped('name'))
            raise UserError(user_warning)

    @api.one
    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_product_qty(self):
        rounding_method = self._context.get('rounding_method', 'UP')
        if not self.product_category == 'Sparepart':
            self.product_qty = self.product_uom._compute_quantity(self.product_uom_qty, self.product_id.uom_id, rounding_method=rounding_method)
        else:
            if self.state == 'draft':
                self.product_qty = self.product_uom._compute_quantity(self.product_uom_qty, self.product_uom, rounding_method=rounding_method)

    def _action_confirm(self, merge=True, merge_into=False):
        """ Confirms stock move or put it in waiting if it's linked to another move.
        :param: merge: According to this boolean, a newly confirmed move will be merged
        in another move of the same picking sharing its characteristics.
        """
        move_create_proc = self.env['stock.move']
        move_to_confirm = self.env['stock.move']
        move_waiting = self.env['stock.move']

        to_assign = {}
        for move in self:
            if move.service_id:
                if move.product_category == 'Sparepart' or move.product_category == 'Bahan':
                    service_line = move.env['service.line'].search([('id', '=', move.service_line_id)], limit=1)
                else:
                    service_line = move.env['service.consumable'].search([('id', '=', move.service_line_id)], limit=1)
                service_line.write({'received': True})

            # if the move is preceeded, then it's waiting (if preceeding move is done, then action_assign has been called already and its state is already available)
            if move.move_orig_ids:
                move_waiting |= move
            else:
                if move.procure_method == 'make_to_order':
                    move_create_proc |= move
                else:
                    move_to_confirm |= move
            if move._should_be_assigned():
                key = (move.group_id.id, move.location_id.id, move.location_dest_id.id)
                if key not in to_assign:
                    to_assign[key] = self.env['stock.move']
                to_assign[key] |= move

        # create procurements for make to order moves
        for move in move_create_proc:
            values = move._prepare_procurement_values()
            origin = (move.group_id and move.group_id.name or (move.origin or move.picking_id.name or "/"))
            self.env['procurement.group'].run(move.product_id, move.product_uom_qty, move.product_uom, move.location_id, move.rule_id and move.rule_id.name or "/", origin,
                                              values)

        move_to_confirm.write({'state': 'confirmed'})
        (move_waiting | move_create_proc).write({'state': 'waiting'})

        # assign picking in batch for all confirmed move that share the same details
        for moves in to_assign.values():
            moves._assign_picking()
        self._push_apply()
        if merge:
            return self._merge_moves(merge_into=merge_into)
        return self

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_category == 'Sparepart':
            category = self.product_id.categ_id.name
            if category not in ['Sparepart', 'Bahan']:
                raise UserError(_('%s tidak termasuk kategori Sparepart atau Bahan' % (self.product_id.name)))
            service_line = self.env['service.line'].search([('id', '=', self.service_line_id)], limit=1)
            cost = service_line.cost_unit
            if service_line.supply_type == 'self':  # and cost == 0:
                # if self.product_id.standard_price == 0:
                #     raise UserError(_('Product "%s" belum memiliki harga standar') % self.product_id.name)
                cost = self.product_id.standard_price
            service_line.write({'product_id': self.product_id.id, 'cost_unit': cost})
            if not self.supply_type:
                self.supply_type = service_line.supply_type

        product = self.product_id.with_context(lang=self.partner_id.lang or self.env.user.lang)
        self.product_uom = product.uom_id.id
        return {'domain': {'product_uom': [('category_id', '=', product.uom_id.category_id.id)]}}

    @api.multi
    def write(self, values):
        lines = super(StockMove, self).write(values)
        return lines

    @api.multi
    def unlink(self):
        for item in self:
            service_line = item.env['service.line'].search([('id', '=', item.service_line_id)], limit=1)
            if item.product_category == 'Sparepart' or item.product_category == 'Bahan':
                if service_line and not service_line.delete_flag:
                    raise UserError(_('Silakan meminta bagian Produksi agar menandai item ini untuk dihapus,'
                                        ' dengan klik icon Delete'))

            res = super(StockMove, item).unlink()
            if service_line:
                service_line.unlink()
            return res

    def _action_assign(self):
        """ Reserve stock moves by creating their stock move lines. A stock move is
        considered reserved once the sum of `product_qty` for all its move lines is
        equal to its `product_qty`. If it is less, the stock move is considered
        partially available.
        """
        assigned_moves = self.env['stock.move']
        partially_available_moves = self.env['stock.move']
        # Read the `reserved_availability` field of the moves out of the loop to prevent unwanted
        # cache invalidation when actually reserving the move.
        reserved_availability = {move: move.reserved_availability for move in self}
        roundings = {move: move.product_id.uom_id.rounding for move in self}
        move_line_vals_list = []
        for move in self.filtered(lambda m: m.state in ['confirmed', 'waiting', 'partially_available']):
            if move.product_id and move.supply_type == 'self':
                if move.product_id.standard_price == 0:
                    raise UserError(_('Product "%s" belum memiliki harga standar') % move.product_id.name)
                    
            rounding = roundings[move]
            missing_reserved_uom_quantity = move.product_uom_qty - reserved_availability[move]
            missing_reserved_quantity = move.product_uom._compute_quantity(missing_reserved_uom_quantity, move.product_id.uom_id, rounding_method='HALF-UP')
            if move.location_id.should_bypass_reservation()\
                    or move.product_id.type == 'consu':
                # create the move line(s) but do not impact quants
                if move.product_id.tracking == 'serial' and (move.picking_type_id.use_create_lots or move.picking_type_id.use_existing_lots):
                    for i in range(0, int(missing_reserved_quantity)):
                        move_line_vals_list.append(move._prepare_move_line_vals(quantity=1))
                else:
                    to_update = move.move_line_ids.filtered(lambda ml: ml.product_uom_id == move.product_uom and
                                                            ml.location_id == move.location_id and
                                                            ml.location_dest_id == move.location_dest_id and
                                                            ml.picking_id == move.picking_id and
                                                            not ml.lot_id and
                                                            not ml.package_id and
                                                            not ml.owner_id)
                    if to_update:
                        to_update[0].product_uom_qty += missing_reserved_uom_quantity
                    else:
                        move_line_vals_list.append(move._prepare_move_line_vals(quantity=missing_reserved_quantity))
                assigned_moves |= move
            else:
                if not move.move_orig_ids:
                    if move.procure_method == 'make_to_order':
                        continue
                    # If we don't need any quantity, consider the move assigned.
                    need = missing_reserved_quantity
                    if float_is_zero(need, precision_rounding=rounding):
                        assigned_moves |= move
                        continue
                    # Reserve new quants and create move lines accordingly.
                    forced_package_id = move.package_level_id.package_id or None
                    available_quantity = self.env['stock.quant']._get_available_quantity(move.product_id, move.location_id, package_id=forced_package_id)
                    if available_quantity <= 0:
                        continue
                    taken_quantity = move._update_reserved_quantity(need, available_quantity, move.location_id, package_id=forced_package_id, strict=False)
                    if float_is_zero(taken_quantity, precision_rounding=rounding):
                        continue
                    if float_compare(need, taken_quantity, precision_rounding=rounding) == 0:
                        assigned_moves |= move
                    else:
                        partially_available_moves |= move
                else:
                    # Check what our parents brought and what our siblings took in order to
                    # determine what we can distribute.
                    # `qty_done` is in `ml.product_uom_id` and, as we will later increase
                    # the reserved quantity on the quants, convert it here in
                    # `product_id.uom_id` (the UOM of the quants is the UOM of the product).
                    move_lines_in = move.move_orig_ids.filtered(lambda m: m.state == 'done').mapped('move_line_ids')
                    keys_in_groupby = ['location_dest_id', 'lot_id', 'result_package_id', 'owner_id']

                    def _keys_in_sorted(ml):
                        return (ml.location_dest_id.id, ml.lot_id.id, ml.result_package_id.id, ml.owner_id.id)

                    grouped_move_lines_in = {}
                    for k, g in groupby(sorted(move_lines_in, key=_keys_in_sorted), key=itemgetter(*keys_in_groupby)):
                        qty_done = 0
                        for ml in g:
                            qty_done += ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
                        grouped_move_lines_in[k] = qty_done
                    move_lines_out_done = (move.move_orig_ids.mapped('move_dest_ids') - move)\
                        .filtered(lambda m: m.state in ['done'])\
                        .mapped('move_line_ids')
                    # As we defer the write on the stock.move's state at the end of the loop, there
                    # could be moves to consider in what our siblings already took.
                    moves_out_siblings = move.move_orig_ids.mapped('move_dest_ids') - move
                    moves_out_siblings_to_consider = moves_out_siblings & (assigned_moves + partially_available_moves)
                    reserved_moves_out_siblings = moves_out_siblings.filtered(lambda m: m.state in ['partially_available', 'assigned'])
                    move_lines_out_reserved = (reserved_moves_out_siblings | moves_out_siblings_to_consider).mapped('move_line_ids')
                    keys_out_groupby = ['location_id', 'lot_id', 'package_id', 'owner_id']

                    def _keys_out_sorted(ml):
                        return (ml.location_id.id, ml.lot_id.id, ml.package_id.id, ml.owner_id.id)

                    grouped_move_lines_out = {}
                    for k, g in groupby(sorted(move_lines_out_done, key=_keys_out_sorted), key=itemgetter(*keys_out_groupby)):
                        qty_done = 0
                        for ml in g:
                            qty_done += ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
                        grouped_move_lines_out[k] = qty_done
                    for k, g in groupby(sorted(move_lines_out_reserved, key=_keys_out_sorted), key=itemgetter(*keys_out_groupby)):
                        grouped_move_lines_out[k] = sum(self.env['stock.move.line'].concat(*list(g)).mapped('product_qty'))
                    available_move_lines = {key: grouped_move_lines_in[key] - grouped_move_lines_out.get(key, 0) for key in grouped_move_lines_in.keys()}
                    # pop key if the quantity available amount to 0
                    available_move_lines = dict((k, v) for k, v in available_move_lines.items() if v)

                    if not available_move_lines:
                        continue
                    for move_line in move.move_line_ids.filtered(lambda m: m.product_qty):
                        if available_move_lines.get((move_line.location_id, move_line.lot_id, move_line.result_package_id, move_line.owner_id)):
                            available_move_lines[(move_line.location_id, move_line.lot_id, move_line.result_package_id, move_line.owner_id)] -= move_line.product_qty
                    for (location_id, lot_id, package_id, owner_id), quantity in available_move_lines.items():
                        need = move.product_qty - sum(move.move_line_ids.mapped('product_qty'))
                        # `quantity` is what is brought by chained done move lines. We double check
                        # here this quantity is available on the quants themselves. If not, this
                        # could be the result of an inventory adjustment that removed totally of
                        # partially `quantity`. When this happens, we chose to reserve the maximum
                        # still available. This situation could not happen on MTS move, because in
                        # this case `quantity` is directly the quantity on the quants themselves.
                        available_quantity = self.env['stock.quant']._get_available_quantity(
                            move.product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=True)
                        if float_is_zero(available_quantity, precision_rounding=rounding):
                            continue
                        taken_quantity = move._update_reserved_quantity(need, min(quantity, available_quantity), location_id, lot_id, package_id, owner_id)
                        if float_is_zero(taken_quantity, precision_rounding=rounding):
                            continue
                        if float_is_zero(need - taken_quantity, precision_rounding=rounding):
                            assigned_moves |= move
                            break
                        partially_available_moves |= move
        self.env['stock.move.line'].create(move_line_vals_list)
        partially_available_moves.write({'state': 'partially_available'})
        assigned_moves.write({'state': 'assigned'})
        self.mapped('picking_id')._check_entire_pack()

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    # service_line_id = fields.Many2one('service.line')
    product_alias = fields.Char('Product Alias')
    