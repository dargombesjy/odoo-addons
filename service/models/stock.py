# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from .service import SUPPLY_TYPES

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
        not_valid = self.mapped('move_lines').filtered(lambda move: move.picking_type_id.name == 'Pick' and (move.vendor_qty == 0 or not move.vendor_date))
        if not_valid:
            raise UserError(_('Qty. Terima dan Tgl. Terima harus diisi'))
        
        if self.picking_type_id.name == 'Pick':
            to_receive = self.mapped('move_lines')\
                .filtered(lambda move:move.supply_type == 'vendor' and move.product_category == 'Sparepart'\
                and move.vendor_id and move.vendor_qty > 0 and move.vendor_date and not move.auto_receipt_id)
            if to_receive:
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
        return True
    
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
        
        picking = Picking.create({
                    # 'name': '',
                    'service_id': self.service_id.id,
                    'origin': 'receipt_4: %s' % (self.name),
                    'eq_name': self.eq_name,
                    'eq_make': self.eq_make,
                    'eq_model': self.eq_model,
                    'move_type': 'one',
                    'partner_id': self.partner_id.id,
                    'picking_type_id': pick.id,
                    'location_id': source.id,
                    'location_dest_id': self.location_id.id,
                    'state': 'draft',
                })
        # if self.picking_type_id.name == 'Pick':
        for move in move_lines:
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
                    'name': 'receipt_4: %s' % (move.name),
                    'date': move.vendor_date,
                    'product_id': move.product_id.id,
                    'product_uom_qty': move.product_uom_qty,
                    'product_uom': move.product_uom.id,
                    'product_category': move.product_category,
                    'supply_type': 'vendor',
                    'partner_id': move.picking_id.partner_id.id,
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
                    'service_id': pick.service_id.id,
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
            service_line = self.env['service.line'].search([('id', '=', self.service_line_id)], limit=1)
            cost = service_line.cost_unit
            if service_line.supply_type == 'self' and cost == 0:
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
        for line in self:
            if line.product_id and line.supply_type == 'self':
                if line.product_id.standard_price == 0:
                    raise UserError(_('Product "%s" belum memiliki harga standar') % line.product_id.name)
        return lines
    
    # def _generate_receipt(self):
        # move = self.env['stock.move']
        # warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.service_id.company_id.id)], limit=1)
        # pick = self.env['stock.picking.type'].search([('name', '=', 'Receipts'), ('warehouse_id', '=', warehouse.id)], limit=1)
        # source = 8
        # destination = pick.default_location_dest_id
        # if self.supply_type == 'vendor':
            # move.create({
                # 'service_id': self.service_id,
                # 'service_line_id': self.service_line_id,
                # 'name': self.name,
                # 'product_category': self.product_category,
                # 'picking_type_id': pick.id,
                # 'product_id': self.product_id.id,
                # 'product_uom_qty': self.product_uom_qty,
                # 'product_uom': self.product_uom.id,
                # 'package_id': False,
                # 'package_level_id': False,
                # 'location_id': source,
                # 'location_dest_id': destination,})

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    # service_line_id = fields.Many2one('service.line')
    product_alias = fields.Char('Product Alias')
    