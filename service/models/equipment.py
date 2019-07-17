# -*- coding: utf-8 -*-
from odoo import fields, models

class ServiceEquipmentMake(models.Model):
    _name = 'service.equipment.make'
    _description = 'Equipment manufacturer'

    name = fields.Char('Manufacturer', required=True)

class ServiceEquipment(models.Model):
    _name = 'service.equipment'
    _description = 'Service Equipment master'

    name = fields.Char('License Number', required=True)
    make = fields.Many2one('service.equipment.make', 'Manufacturer')
    model = fields.Char('Model')
    partner_id = fields.Many2one('res.partner', 'Customer')
