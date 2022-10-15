# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from email.policy import default
# from odoo.addons import decimal_precision as dp


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def action_print_invoice_or(self):
        return self.env.ref('zaccount.action_invoice_or').report_action(self)

    @api.multi
    def action_invoice_aab(self):
        return self.env.ref('zaccount.action_invoice_aab').report_action(self)
    
    @api.multi
    def action_set_draft(self):
        if self.move_id:
            if self.move_id.state == 'draft':
                self.move_id.unlink()
            else:
                m_lines = self.move_id.reverse_moves()
                # if m_lines == []:
                    # self.move_id.unlink()
                self.move_id = None
        return self.write({'state': 'draft'})

    @api.one
    def action_recompute_wht(self):
        round_curr = self.currency_id.round
        if not self.wht_tax:
            tax = self.prepare_wht_tax()
            self.env['account.invoice.tax'].create(tax['val'])
        else:
            wht = self.env['account.invoice.tax'].search([('invoice_id', '=', self.id), ('tax_id', '=', self.wht_tax[0].id)], limit=1)
            tax = self.prepare_wht_tax()
            wht.write({'amount': tax['val']['amount']})
        self.amount_wht = sum(round_curr(wh.amount_total) for wh in self.tax_line_ids.filtered(lambda w: w.tax_id == self.wht_tax))

    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'tax_line_ids.amount_rounding',
                 'currency_id', 'company_id', 'date_invoice', 'type')
    def _compute_wht(self):
        self._calc_wht()
    
    def _calc_wht(self):
        round_curr = self.currency_id.round
        # wht_tax = self.partner_id.wht_tax
        wht_tax = self.partner_id.get_wht(self.company_id)
        wht_proportion = self.partner_id.wht_proportion
        wht_base = sum(line.price_subtotal for line in self.invoice_line_ids.filtered(lambda l: l.product_category == 'Service Fee'))

        self.wht_base = wht_base
        self.sub_material = 0
        self.wht_tax = wht_tax
        self.wht_proportion = wht_proportion
        if wht_proportion > 0:
            wht_base_rev = wht_base * wht_proportion
            self.wht_base = wht_base_rev
            self.sub_material = wht_base - wht_base_rev
        self.sub_spareparts = sum(sp.price_subtotal for sp in self.invoice_line_ids.filtered(lambda s: s.product_category == 'Sparepart'))
        other = sum(oth.price_subtotal for oth in self.invoice_line_ids.filtered(lambda o: o.product_category == 'Service Other'))
        self.sub_others = other + self.own_risk
        self.amount_wht = sum(round_curr(wh.amount_total) for wh in self.tax_line_ids.filtered(lambda w: w.tax_id == self.wht_tax))

    def prepare_wht_tax(self):
        # ctx = dict(self._context)
        # round_curr = self.currency_id.round
        # account_invoice_tax = self.env['account.invoice.tax']
        res = {}
        wht_line = self.invoice_line_ids.search([('product_category', '=', 'Service Fee')], limit=1)
        if wht_line:
            wht_tax = self.wht_tax.compute_all(price_unit=self.wht_base, currency=self.currency_id, partner=self.partner_id)['taxes']
            wht_val = self._prepare_tax_line_vals(wht_line, wht_tax[0])
            # val['manual'] = True # set to manual, so it would not be overwrited by onchange line ids
            wht_key = self.env['account.tax'].browse(wht_tax[0]['id']).get_grouping_key(wht_val)
            # account_invoice_tax.create(wht_val)
            res = {'key': wht_key, 'val': wht_val}
        return res
        # dummy write on self to trigger recomputations
        # return self.with_context(ctx).write({'invoice_line_ids': []})

    def create_wht_tax(self):
        wht = self.prepare_wht_tax()
        self.env['account.invoice.tax'].create(wht['val'])

    # @api.onchange('invoice_line_ids')
    # def _onchange_invoice_line_ids(self):
    #     taxes_grouped = self.get_taxes_values()
    #     # wht = self.prepare_wht_tax()
    #     # taxes_grouped[wht['key']] = wht['val']
    #     tax_lines = self.tax_line_ids.filtered('manual')
    #     for tax in taxes_grouped.values():
    #         tax_lines += tax_lines.new(tax)
    #     self.tax_line_ids = tax_lines
    #     return

    @api.multi
    def get_taxes_values(self):
        tax_grouped = {}
        round_curr = self.currency_id.round
        account_tax = self.env['account.tax']
        wht_line = False
        for line in self.invoice_line_ids:
            if not line.account_id:
                continue
            if self.wht_tax:
                if line.product_category == 'Service Fee':
                    wht_line = line
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.invoice_line_tax_ids.compute_all(price_unit, self.currency_id, line.quantity, line.product_id, self.partner_id)['taxes']
            for tax in taxes:
                val = self._prepare_tax_line_vals(line, tax)
                # key = self.env['account.tax'].browse(tax['id']).get_grouping_key(val)
                key = account_tax.browse(tax['id']).get_grouping_key(val)
                if key not in tax_grouped:
                    tax_grouped[key] = val
                    tax_grouped[key]['base'] = round_curr(val['base'])
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += round_curr(val['base'])
        if wht_line:
            wht_tax_list = self.wht_tax.compute_all(price_unit=self.wht_base, currency=self.currency_id, partner=self.partner_id)
            wht_tax = wht_tax_list['taxes']
            wht_val = self._prepare_tax_line_vals(wht_line, wht_tax[0])
            wht_key = account_tax.browse(wht_tax[0]['id']).get_grouping_key(wht_val)
            tax_grouped[wht_key] = wht_val
            tax_grouped[wht_key]['base'] = round_curr(wht_val['base'])
        return tax_grouped

    # override standard methods
    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'tax_line_ids.amount_rounding',
                 'currency_id', 'company_id', 'date_invoice', 'type')
    def _compute_amount(self):
        round_curr = self.currency_id.round
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids)
        tax_total = sum(round_curr(line.amount_total) for line in self.tax_line_ids)
        # self.amount_tax = sum(round_curr(line.amount_total) for line in self.tax_line_ids)
        # self.amount_total = self.amount_untaxed + self.amount_tax
        self.amount_tax = sum(round_curr(ln.amount_total) for ln in self.tax_line_ids.filtered(lambda w: w.tax_id != self.wht_tax))
        # self.amount_tax = tax_total + self.amount_wht
        if self.amount_untaxed < self.own_risk:
            self.amount_total = self.amount_untaxed
        else:
            self.amount_total = self.amount_untaxed + self.own_risk
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

    # # override standard methods
    # @api.onchange('invoice_line_ids')
    # def _onchange_invoice_line_ids(self):
    #     taxes_grouped = self.get_taxes_values()
    #     tax_lines = self.tax_line_ids.filtered('manual')
    #     for tax in taxes_grouped.values():
    #         tax_lines += tax_lines.new(tax)
    #     self.tax_line_ids = tax_lines
    #     if self.move_id:
    #         move_lines = self._rebuild_move_line()

    #     return

    # def _rebuild_move_line(self):
    #     inv = self
    #     # create move lines (one per invoice line + eventual taxes and analytic lines)
    #     iml = inv.invoice_line_move_line_get()
    #     iml += inv.tax_line_move_line_get()

    #     diff_currency = inv.currency_id != company_currency
    #     # create one move line for the total and possibly adjust the other lines amount
    #     total, total_currency, iml = inv.compute_invoice_totals(company_currency, iml)

    #     name = inv.name or ''
    #     if inv.payment_term_id:
    #         totlines = inv.payment_term_id.with_context(currency_id=company_currency.id).compute(total, inv.date_invoice)[0]
    #         res_amount_currency = total_currency
    #         for i, t in enumerate(totlines):
    #             if inv.currency_id != company_currency:
    #                 amount_currency = company_currency._convert(t[1], inv.currency_id, inv.company_id, inv._get_currency_rate_date() or fields.Date.today())
    #             else:
    #                 amount_currency = False

    #             # last line: add the diff
    #             res_amount_currency -= amount_currency or 0
    #             if i + 1 == len(totlines):
    #                 amount_currency += res_amount_currency

    #             iml.append({
    #                 'type': 'dest',
    #                 'name': name,
    #                 'price': t[1],
    #                 'account_id': inv.account_id.id,
    #                 'date_maturity': t[0],
    #                 'amount_currency': diff_currency and amount_currency,
    #                 'currency_id': diff_currency and inv.currency_id.id,
    #                 'invoice_id': inv.id
    #             })
    #     else:
    #         iml.append({
    #             'type': 'dest',
    #             'name': name,
    #             'price': total,
    #             'account_id': inv.account_id.id,
    #             'date_maturity': inv.date_due,
    #             'amount_currency': diff_currency and total_currency,
    #             'currency_id': diff_currency and inv.currency_id.id,
    #             'invoice_id': inv.id
    #         })
    #     part = self.env['res.partner']._find_accounting_partner(inv.partner_id)
    #     line = [(0, 0, self.line_get_convert(l, part.id)) for l in iml]
    #     line = inv.group_lines(iml, line)

    #     line = inv.finalize_invoice_move_lines(line)
    #     return line

    @api.model
    def create(self, vals):
        if vals['origin_type'] == 'own_risk':
            journal = self.env['account.journal'].search([('code', '=', 'ORINV'), ('company_id', '=', vals['company_id'])], limit=1)
            vals['journal_id'] = journal.id
         
        result = super(AccountInvoice, self).create(vals)
        return result
    
    @api.one
    @api.depends
    def _compute_equipment(self):
        eq = self.service_id.equipment_id
        self.eq_name = eq.name

    @api.onchange('service_id')
    def _onchange_service_id(self):
        self.eq_name = self.service_id.equipment_id.name
        self.origin = self.service_id.name

    origin_type = fields.Selection([
        ('general', 'General'),
        ('service', 'Service'),
        ('own_risk', 'Own Risk'),
        ('warehouse', 'Warehouse'),
        ('entertain', 'Entertain')], 'Origin Type', required=True, default='general')
    service_id = fields.Many2one(
        'service.order', string='Service', copy='False', readonly=True,
        states={'draft': [('readonly', False)]})
    eq_name = fields.Char('No. Plat', compute='_compute_equipment', store=True)
    sub_spareparts = fields.Monetary('Spareparts', compute='_compute_wht', store=True, readonly=True)
    sub_material = fields.Monetary('Material', compute='_compute_wht', store=True, readonly=True)
    sub_others = fields.Monetary('Others', compute='_compute_wht', store=True, readonly=True)
    wht_tax = fields.Many2one('account.tax', string="Withholding Tax", compute='_compute_wht',
        store=True, readonly=True)
    wht_proportion = fields.Float('WHT proportion', compute='_compute_wht', store=True,
        readonly=True)
    wht_base = fields.Monetary('Base Amount WHT', compute='_compute_wht', store=True,
        readonly=True, track_visibility='always')
    amount_wht = fields.Monetary('Amount WHT', compute='_compute_wht', store=True, readonly=True)
    own_risk = fields.Monetary('Own Risk', digits=0)
    bill_printed = fields.Boolean('Billing List Printed')
    

class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    product_category = fields.Char('Category')
    deductible = fields.Boolean('Deductible', default=False)
