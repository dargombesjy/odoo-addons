# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

class ServiceOrder(models.Model):
    _inherit = 'service.order'

    # @api.multi
    # def action_validate(self):
    #     self.ensure_one()
    #     for op in self.operations:
    #         precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
    #         available_qty_owner = self.env['stock.quant']._get_available_quantity(op.product_id, op.location_id, op.lot_id, owner_id=self.partner_id, strict=True)
    #         available_qty_noown = self.env['stock.quant']._get_available_quantity(op.product_id, op.location_id, op.lot_id, strict=True)
    #         for available_qty in [available_qty_owner, available_qty_noown]:
    #             if float_compare(available_qty, op.product_uom_qty, precision_digits=precision) >= 0:
    #                 return True
    #             else:
    #                 return {
    #                     'name': _('Insufficient Quantity'),
    #                     'view_type': 'form',
    #                     'view_mode': 'form',
    #                     'res_model': 'stock.warn.insufficient.qty.service',
    #                     'view_id': self.env.ref('service.stock_warn_insufficient_qty_form_view').id,
    #                     'type': 'ir.actions.act_window',
    #                     'context': {
    #                         'default_product_id': op.product_id.id,
    #                         'default_location_id': op.location_id.id,
    #                         'default_service_id': op.service_id
    #                     },
    #                     'target': 'new'
    #                 }
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
        for service in self:
            service.write({'repaired': True})
            vals = {'state': 'done'}
            # vals['move_id'] = service.action_service_done().get(service.id)
            # if not service.action_service_done():
                # raise UserError('Service not Done')
            if not service.invoiced and service.invoice_method == 'after_repair':
                vals['state'] = '2binvoiced'
            service.write(vals)
        return True

    @api.multi
    def action_service_done(self):
        """ Creates stock move for operation.
        @return: Move  ids of ...

        """
        if self.filtered(lambda service: not service.repaired):
            raise UserError(_('Service must be performed in order to make product moves.'))
        # res = {}
        # precision = self.env['decimal.precission'].precission_get('Product Unit of Measure')
        Move = self.env['stock.move']
        for service in self:
            moves = self.env['stock.move']
            for operation in service.operations:
                # temporarily commented for testing purposes
                # if operation.filtered(lambda line: not line.received):
                    # raise UserError(_('All line sparepart must be received in order to done reparation.'))
                move = Move.create({
                    'name': service.name,
                    'product_id': operation.product_id.id,
                    'product_uom_qty': operation.product_uom_qty,
                    'product_uom': operation.product_uom.id,
                    'partner_id': service.partner_id.id, # service.address_id.id
                    'location_id': operation.location_id.id,
                    'location_dest_id': operation.location_dest_id.id,
                    'move_line_ids': [(0, 0, {
                        'product_id': operation.product_id.id,
                        'product_uom_qty': 0,
                        'product_uom_id': operation.product_uom.id,
                        'qty_done': operation.product_uom_qty,
                        'package_id': False,
                        'result_package_id': False,
                        # 'owner_id': owner_id,
                        'location_id': operation.location_id.id,
                        'location_dest_id': operation.location_dest_id,
                    })],
                    'repair_id': service.id,
                    'origin': service.name,
                })
                moves |= move
                operation.write({'move_id': move.id, 'state': 'done'})
            consumed_lines = moves.mapped('move_line_ids')
            # produced_lines = move.move_line_ids
            # moves |= move
            moves._action_done()
            # produced_lines.write({'consume_line_ids': [(6, 0, consume_lines.ids)]})
        #     res[service.id] = move.id
        # return res
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
