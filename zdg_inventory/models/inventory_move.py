# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.addons.service.models.service import SUPPLY_TYPES


class InventoryMove(models.Model):
	_name = 'inventory.move'
	_description = 'Inventory Custom Move'
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_order = 'create_date desc'

	name = fields.Char('Name', required=True)
	company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env['res.company']._company_default_get('stock.move'),
        index=True, required=True)
	service_id = fields.Many2one('service.order')
	eq_name = fields.Char('No. Plat')
	state = fields.Selection([
        ('draft', 'New'), ('cancel', 'Cancelled'),
        ('waiting', 'Waiting Another Move'),
        ('confirmed', 'Waiting Availability'),
        ('partially_available', 'Partially Available'),
        ('assigned', 'Available'),
        ('done', 'Done')], string='Status',
        copy=False, default='draft', index=True, readonly=True,
        help="* New: When the stock move is created and not yet confirmed.\n"
             "* Waiting Another Move: This state can be seen when a move is waiting for another one, for example in a chained flow.\n"
             "* Waiting Availability: This state is reached when the procurement resolution is not straight forward. It may need the scheduler to run, a component to be manufactured...\n"
             "* Available: When products are reserved, it is set to \'Available\'.\n"
             "* Done: When the shipment is processed, the state is \'Done\'.")
	
	
class InventoryMoveLine(models.Model):
	_name = 'inventory.move.line'
	_description = 'Inventory Move Line'

	name = fields.Char('Name')
	move_id = fields.Many2one('inventory.move')
	service_id = fields.Many2one('service.order')
	service_line_id = fields.Integer('Line Id')
	product_category = fields.Char('Product Category')
	supply_type = fields.Selection(SUPPLY_TYPES, 'Supply Type')
	vendor_id = fields.Many2one('res.partner', 'Vendor')
	product_id = fields.Many2one(
		'product.product', 'Product',
		domain=[('type', 'in', ['product', 'consu'])], index=True, required=False)
	part_number = fields.Char('Kode Part Admin')
	product_uom_qty = fields.Float('Qty.')
	product_uom = fields.Many2one('uom.uom', 'Product Unit od Measure')
	is_done = fields.Boolean('Done?')
	date = fields.Date('Date', default=fields.Date.today)
	state = fields.Selection(related='move_id.state', store=True, related_sudo=False, readonly=False)
	