# -*- coding: utf-8 -*-
from odoo import fields, models, api

class StockMove(models.Model):
    _inherit = 'stock.move'

    service_id = fields.Many2one('service.order')

class ServiceOrder(models.Model):
    _inherit = 'service.order'

    work_stage = fields.Selection([
        ('antri', 'Dalam Antrian'),
        ('bongkar', 'Pembongkaran'),
        ('ketok', 'Ketok'),
        ('dempul', 'Dempul'),
        ('cat', 'Pengecatan'),
        ('finishing', 'Finishing')], string='Stage', default="antri")
    cost_untaxed = fields.Float('Untaxed cost', compute='_cost_untaxed', store=True)
    cost_tax = fields.Float('Taxes', compute='_cost_tax', store=True)
    cost_total = fields.Float('Total cost', compute='_cost_total', store=True)
    purchased = fields.Boolean('PO Created', copy=False, readonly=True)
    purchase_id = fields.Many2one(
        'purchase.order', 'Purchase Order',
        copy=False, readonly=True, track_visibility="onchange")

    @api.one
    def _cost_untaxed(self):
        pass

    @api.one
    def _cost_tax(self):
        pass

    @api.one
    def _cost_total(self):
        pass

class ServiceLine(models.Model):
    _inherit = 'service.line'

    location_id = fields.Many2one(
        'stock.location', 'Source Location', index=True)
    location_dest_id = fields.Many2one(
        'stock.location', 'Dest. Location', index=True)
    move_id = fields.Many2one(
    'stock.move', 'Inventory Move', copy=False, readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], 'Status', default='draft',
        copy=False, readonly=True, required=True,
        help='The status of a repair line is set automatically to the one of the linked repair order.')
    purchased = fields.Boolean('Purchased', copy=False, required=True)
    purchase_line_id = fields.Many2one(
        'purchase.order.line', 'Purchase Line', copy=False)

class ServiceFee(models.Model):
    _inherit = 'service.fee'

    cost_unit = fields.Float('Unit Cost', required=True)
    cost_tax_id = fields.fields.Many2many(
        'account.tax', 'service_operation_line_tax', 'service_operation_line_id', 'tax_id', 'Taxes')
    cost_subtotal = fields.Float('Subtotal', compute='_compute_cost_subtotal', store=True, digits=0)
    purchased = fields.Boolean('Purchased', copy=False, required=True)
    purchase_line_id = fields.Many2one(
        'purchase.order.line', 'Purchase Line', copy=False)

    @api.one
    def _compute_cost_subtotal(self):
        pass
