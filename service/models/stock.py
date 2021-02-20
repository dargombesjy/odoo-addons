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
        move_supply = self.env['stock.move']
        for move in self.move_lines:
            if move.product_category == 'Sparepart' and move.vendor_id and move.vendor_qty > 0:
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
                        'name': move.name,
                        'date': move.vendor_date,
                        'product_id': move.product_id.id, #operation.product_id.id,
                        'product_uom_qty': move.product_uom_qty, #operation.product_uom_qty,
                        'product_uom': move.product_uom.id, #operation.product_uom.id,
                        'partner_id': move.picking_id.partner_id.id, #repair.address_id.id,
                        'location_id': 8, #operation.location_id.id,
                        'location_dest_id': move.location_id.id, #operation.location_dest_id.id,
                        'move_line_ids': [(0, 0, {'product_id': move.product_id.id, #operation.product_id.id,
                                                  #'lot_id': move.lot_id, #operation.lot_id.id,
                                                  'product_uom_qty': move.product_uom_qty,  # bypass reservation here
                                                  'product_uom_id': move.product_uom.id, #operation.product_uom.id,
                                                  'qty_done': move_qty, #operation.product_uom_qty,
                                                  'package_id': False,
                                                  'result_package_id': False,
                                                  #'owner_id': #owner_id,
                                                  'location_id': 8, #move.location_id, #operation.location_id.id, #TODO: owner stuff
                                                  'location_dest_id': move.location_id.id })], #operation.location_dest_id.id,})],
                        'origin': move.service_id.id, #repair.id,
                        'service_id': move.service_id.id, #repair.id,
                        'service_line_id': move.service_line_id, #repair.name,
                    })
                    move.write({'vendor_received': total_received})
                    supply._action_done()

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

class StockMove(models.Model):
    _inherit = 'stock.move'

    service_id = fields.Many2one('service.order')
    service_line_id = fields.Integer('Line Id')
    product_id = fields.Many2one(
        'product.product', 'Product',
        domain=[('type', 'in', ['product', 'consu'])], index=True, required=False)
    product_category = fields.Char('Product Category')
    supply_type = fields.Selection(SUPPLY_TYPES, 'Supply Type')
    vendor_id = fields.Many2one('res.partner', 'Vendor', index=True)
    vendor_qty = fields.Float('Qty. Terima')
    vendor_date = fields.Date('Tgl. Terima')
    vendor_received = fields.Float('Recv')
    receiver = fields.Char('Penerima')
    received_date = fields.Date('Tgl. Ambil')
    
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

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    # service_line_id = fields.Many2one('service.line')
    product_alias = fields.Char('Product Alias')