# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    product_category = fields.Char('Category')
