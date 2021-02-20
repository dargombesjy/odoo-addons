# -*- coding: utf-8 -*-
from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    make_id = fields.Many2one('service.equipment.make', 'Manufacturer')
    model_id = fields.Many2one('service.equipment.variant', 'Model')
    generic_name = fields.Char('Nama umum')
    note = fields.Char('Keterangan')