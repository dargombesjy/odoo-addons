# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    is_insurance = fields.Boolean('Insurance')
    wht_tax = fields.Many2one('account.tax', string="Withholding Tax")
        # fields.Many2many('account.tax', 'service_operation_line_tax', 'service_operation_line_id', 'tax_id', 'WHT Taxes')
    wht_proportion = fields.Float('WHT proportion', default=1.0)
    wht_treshold = fields.Float('WHT Treshold', default=0.0)
