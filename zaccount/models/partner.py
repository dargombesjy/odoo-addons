# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    is_insurance = fields.Boolean('Insurance')
    wht_tax = fields.Many2one('account.tax', string="Withholding Tax")
        # fields.Many2many('account.tax', 'service_operation_line_tax', 'service_operation_line_id', 'tax_id', 'WHT Taxes')
    wht_proportion = fields.Float('WHT proportion', default=1.0)

    def get_wht(self, company):
        if company == self.wht_tax.company_id:
            return self.wht_tax
        else:
            wht = self.env['account.tax'].search([('name', '=', self.wht_tax.name), ('company_id', '=', company.id)], limit=1)
            return wht

    @api.multi
    def write(self, vals):
        # if vals['wht_proportion']:
        if 'wht_proportion' in vals:
            if vals['wht_proportion'] > 1.0:
                raise UserError(_('WHT Proportion dalam desimal harus kurang dari atau sama dengan 1'))
        res = super(ResPartner, self).write(vals)
        return res