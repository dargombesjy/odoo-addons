# -*- coding: utf-8 -*-
from odoo import models, fields, api
# from odoo.addons import decimal_precision as dp


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'tax_line_ids.amount_rounding',
                 'currency_id', 'company_id', 'date_invoice', 'type')
    def _compute_wht(self):
        wht_tax = self.partner_id.wht_tax
        wht_proportion = self.partner_id.wht_proportion
        wht_base = sum(line.price_subtotal for line in self.invoice_line_ids.filtered(lambda l: l.product_category == 'Service Fee'))
        wht_base_rev = wht_base * wht_proportion

        self.wht_tax = wht_tax
        self.wht_proportion = wht_proportion
        self.wht_base = wht_base_rev

    def create_wht_tax(self):
        ctx = dict(self._context)
        account_invoice_tax = self.env['account.invoice.tax']
        tax = self.wht_tax.compute_all(price_unit=self.wht_base, currency=self.currency_id, partner=self.partner_id)['taxes']
        line = self.invoice_line_ids.search([('product_category', '=', 'Service Fee')], limit=1)
        val = self._prepare_tax_line_vals(line, tax[0])
        # val['manual'] = True # set to manual, so it would not be overwrited by onchange line ids
        account_invoice_tax.create(val)

        # dummy write on self to trigger recomputations
        return self.with_context(ctx).write({'invoice_line_ids': []})

    @api.multi
    def get_taxes_values(self):
        tax_grouped = {}
        round_curr = self.currency_id.round
        for line in self.invoice_line_ids:
            if not line.account_id:
                continue
            if line.product_category == 'Service Fee':
                wht_line = line
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.invoice_line_tax_ids.compute_all(price_unit, self.currency_id, line.quantity, line.product_id, self.partner_id)['taxes']
            for tax in taxes:
                val = self._prepare_tax_line_vals(line, tax)
                key = self.env['account.tax'].browse(tax['id']).get_grouping_key(val)

                if key not in tax_grouped:
                    tax_grouped[key] = val
                    tax_grouped[key]['base'] = round_curr(val['base'])
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += round_curr(val['base'])
        wht_tax = self.wht_tax.compute_all(price_unit=self.wht_base, currency=self.currency_id, partner=self.partner_id)['taxes']
        wht_val = self._prepare_tax_line_vals(wht_line, wht_tax[0])
        wht_key = self.env['account.tax'].browse(wht_tax[0]['id']).get_grouping_key(wht_val)
        tax_grouped[wht_key] = wht_val
        tax_grouped[wht_key]['base'] = round_curr(wht_val['base'])
        return tax_grouped

    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'tax_line_ids.amount_rounding',
                 'currency_id', 'company_id', 'date_invoice', 'type')
    def _compute_amount(self):
        round_curr = self.currency_id.round
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids)
        self.amount_tax = sum(round_curr(line.amount_total) for line in self.tax_line_ids)
        self.amount_total = self.amount_untaxed + self.amount_tax - self.own_risk
        amount_total_company_signed = self.amount_total
        amount_untaxed_signed = self.amount_untaxed
        if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
            currency_id = self.currency_id
            amount_total_company_signed = currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date_invoice or fields.Date.today())
            amount_untaxed_signed = currency_id._convert(self.amount_untaxed, self.company_id.currency_id, self.company_id, self.date_invoice or fields.Date.today())
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        self.amount_total_company_signed = amount_total_company_signed * sign
        self.amount_total_signed = self.amount_total * sign
        self.amount_untaxed_signed = amount_untaxed_signed * sign

    # def _onchange_partner_id(self):
    #     res = super(AccountInvoice, self)._onchange_partner_id()
    #     return res

    wht_tax = fields.Many2one('account.tax', string="Withholding Tax", compute='_compute_wht',
        store=True, readonly=True)
    wht_proportion = fields.Float('WHT proportion', compute='_compute_wht', store=True,
        readonly=True)
    wht_base = fields.Monetary('Base Amount WHT', compute='_compute_wht', store=True,
        readonly=True, track_visibility='always')
    own_risk = fields.Float('Own Risk', digits=0)


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    product_category = fields.Char('Category')
