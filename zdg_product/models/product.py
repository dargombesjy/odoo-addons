from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    make_id = fields.Many2one('service.equipment.make', 'Manufacturer')
    model_id = fields.Many2one('service.equipment.variant', 'Model')
    note = fields.Char('Keterangan')