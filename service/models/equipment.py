# -*- coding: utf-8 -*-
from odoo import fields, models, api

class ServiceEquipmentMake(models.Model):
    _name = 'service.equipment.make'
    _description = 'Equipment manufacturer'

    name = fields.Char('Manufacturer', required=True)

class ServiceEquipmentVariant(models.Model):
    _name = 'service.equipment.variant'
    _description = 'Equipment models variant'

    name = fields.Char('Model name')
    manufacturer_id = fields.Many2one('service.equipment.make', 'Manufacturer')

class ServiceEquipment(models.Model):
    _name = 'service.equipment'
    _description = 'Service Equipment master'

    name = fields.Char('License Number', required=True)
    make_id = fields.Many2one('service.equipment.make', 'Manufacturer')
    model_id = fields.Many2one('service.equipment.variant', 'Model')
    manuf_year = fields.Char('Year')
    chassis_no = fields.Char('Chassis No.')
    engine_no = fields.Char('Engine No.')
    base_colour = fields.Char('Base Colour')
    partner_id = fields.Many2one('res.partner', 'Customer')

    # @api.one
    def get_details(self):
        # return self.chassis_no
        return {
            'make': self.make_id.name, 'model': self.model_id.name, 'manuf_year': self.manuf_year,
            'chassis_no': self.chassis_no, 'engine_no': self.engine_no, 'base_colour': self.base_colour,
        }
