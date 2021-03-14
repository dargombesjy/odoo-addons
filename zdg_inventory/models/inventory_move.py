# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.addons.service.models.service import SUPPLY_TYPES


class InventoryMove(models.Model):
	_name = 'inventory.move'
	_description = 'Inventory Custom Move'

	name = fields.Char('Name', required=True)
	company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env['res.company']._company_default_get('stock.move'),
        index=True, required=True)
	service_id = fields.Many2one('service.order')
	
	
class InventoryMoveLine(models.Model):
	_name = 'inventory.move.line'
	_description = 'Inventory Move Line'

	name = fields.Char('Name')
	service_id = fields.Many2one('service.order')
	service_line_id = fields.Integer('Line Id')
	product_id = fields.Many2one(
		'product.product', 'Product',
		domain=[('type', 'in', ['product', 'consu'])], index=True, required=False)
	product_category = fields.Char('Product Category')
	supply_type = fields.Selection(SUPPLY_TYPES, 'Supply Type')
	vendor_id = fields.Many2one('res.partner', 'Vendor')
	qty = fields.Float('Qty.')
	is_done = fields.Boolean('Done?')
	date = fields.Date('Date', default=fields.Date.today)
	