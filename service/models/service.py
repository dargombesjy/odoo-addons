# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError

class Partner(models.Model):
    _inherit = 'res.partner'

    is_insurance = fields.Boolean('Insurance', default=False)

class ServiceOrder(models.Model):
    _name = 'service.order'
    _description = 'Service Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    def _get_default_currency_id(self):
        return self.env.user.company_id.currency_id.id

    name = fields.Char(
        'Service reference',
        default=lambda self: self.env['ir.sequence'].next_by_code('service.order'),
        copy=False, required=True)
    # states={'confirmed': [('readonly', True)]})
    bill_type = fields.Selection([
        ('self', 'Bill to Customer'),
        ('claim', 'Bill to Insurance')], string="Billing Type", copy=False, required=True)
    claim_reference = fields.Char('AMC')
    claim_id = fields.Char('Claim ID')
    equipment_id = fields.Many2one(
        'service.equipment', 'Equipment', copy=False, required=True)
    # readonly=True, states={'draft': [('readonly', False)]})
    partner_id = fields.Many2one(
        'res.partner', 'Customer', index=True,
        domain=[('is_insurance', '=', True)])
    insurance_id = fields.Many2one(
        'res.partner', 'Insurance', index=True,
        domain=[('is_insurance', '=', False)])
    # states={'confirmed': [('readonly', True)]})
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('cancel', 'Cancelled'),
        ('confirmed', 'Confirmed'),
        ('under_repair', 'Under Repair'),
        ('ready', 'Ready to Repair'),
        ('2binvoiced', 'To be Invoiced'),
        ('invoice_except', 'Invoice Exception'),
        ('done', 'Repaired')],
        string='Status', copy=False, default='draft', readonly=True,
        track_visibility='onchange',
        help="* The \'Draft\' status is used when a user is encoding a new and unconfirmed repair order.\n"
             "* The \'Confirmed\' status is used when a user confirms the repair order.\n"
             "* The \'Ready to Repair\' status is used to start to repairing, user can start repairing only after repair order is confirmed.\n"
             "* The \'To be Invoiced\' status is used to generate the invoice before or after repairing done.\n"
             "* The \'Done\' status is set when repairing is completed.\n"
             "* The \'Cancelled\' status is used when user cancel repair order.")
    operations = fields.One2many(
        'service.line', 'service_id', 'Part', copy=True)
    # readonly=True, states={'draft': [('readonly', False)]})
    fees_lines = fields.One2many(
        'service.fee', 'service_id', copy=True)
    # readonly=True states={'draft': [('readonly', False)]})
    partner_invoice_id = fields.Many2one('res.partner', 'Invoicing Address')
    invoice_method = fields.Selection([
        ("none", "No Invoice"),
        ("b4repair", "Before Repair"),
        ("after_repair", "After Repair")], string="Invoice Method",
        default='after_repair', index=True, readonly=True, required=True,
        states={'draft': [('readonly', False)]},
        help='Selecting \'Before Repair\' or \'After Repair\' will allow you to generate invoice before or after the repair is done respectively. \'No invoice\' means you don\'t want to generate invoice for this repair order.')
    currency_id = fields.Many2one('res.currency', 'Currency', default=_get_default_currency_id, required=True)
    invoice_id = fields.Many2one(
        'account.invoice', 'Invoice',
        copy=False, readonly=True, track_visibility="onchange")
    amount_untaxed = fields.Float('Untaxed Amount', compute='_amount_untaxed', store=True)
    amount_tax = fields.Float('Taxes', compute='_amount_tax', store=True)
    amount_total = fields.Float('Total', compute='_amount_total', store=True)

    @api.onchange('equipment_id')
    def onchange_equipment_id(self):
        self.partner_id = self.equipment_id.partner_id.id

    @api.one
    @api.depends('operations.price_subtotal', 'invoice_method', 'fees_lines.price_subtotal')
    def _amount_untaxed(self):
        total = sum(operation.price_subtotal for operation in self.operations)
        total += sum(fee.price_subtotal for fee in self.fees_lines)
        self.amount_untaxed = total

    @api.one
    @api.depends('operations.price_unit', 'operations.product_uom_qty', 'operations.product_id',
                 'fees_lines.price_unit', 'fees_lines.product_uom_qty', 'fees_lines.product_id',
                 'currency_id', 'partner_id')
    def _amount_tax(self):
        val = 0.0
        for operation in self.operations:
            if operation.tax_id:
                tax_calculate = operation.tax_id.compute_all(operation.price_unit, self.currency_id, operation.product_uom_qty, operation.product_id, self.partner_id)
                for c in tax_calculate['taxes']:
                    val += c['amount']
        for fee in self.fees_lines:
            if fee.tax_id:
                tax_calculate = fee.tax_id.compute_all(fee.price_unit, self.currency_id, fee.product_uom_qty, fee.product_id, self.partner_id)
                for c in tax_calculate['taxes']:
                    val += c['amount']
        self.amount_tax = val

    @api.one
    @api.depends('amount_untaxed', 'amount_tax')
    def _amount_total(self):
        self.amount_total = self.currency_id.round(self.amount_untaxed + self.amount_tax)

    _sql_constraints = [
        ('name', 'unique (name)', 'The name of the Service Order must be unique!')
    ]

    @api.multi
    def button_dummy(self):
        # TDE FIXME: this button is very interesting
        return True

    @api.multi
    def action_service_confirm(self):
        if self.filtered(lambda service: service.state != 'draft'):
            raise UserError(_("Only draft repair can be confirmed."))
        before_repair = self.filtered(lambda service: service.invoice_method == 'b4repair')
        before_repair.write({'state': '2binvoiced'})
        to_confirm = self - before_repair
        to_confirm_operations = to_confirm.mapped('operations')
        to_confirm_operations.write({'state': 'confirmed'})
        to_confirm.write({'state': 'confirmed'})
        return True

    @api.multi
    def action_send_mail(self):
        pass

    @api.multi
    def action_print_service_order(self):
        return self.env.ref('service.action_report_service_order').report_action(self)

class ServiceLine(models.Model):
    _name = 'service.line'
    _description = 'Service Line (Part)'

    name = fields.Text('Description', required=True)
    service_id = fields.Many2one(
        'service.order', 'Service Order reference',
        index=True, ondelete='cascade')
    # type = fields.Selection([
    #     ('add', "Add"),
    #     ('remove', "Remove")], 'Type', required=True)
    supply_type = fields.Selection([
        ('self', 'Self Supply'),
        ('vendor', 'Vendor Supply')], 'Supply Type', index=True, required=True)
    product_id = fields.Many2one('product.product', 'Sparepart', required=True)
    product_uom_qty = fields.Float('Quantity', default=1.0, required=True)
    product_uom = fields.Many2one(
        'uom.uom', 'Product Unit od Measure')
    price_unit = fields.Float('Unit Price', required=True)
    tax_id = fields.Many2many(
        'account.tax', 'service_operation_line_tax', 'service_operation_line_id', 'tax_id', 'Taxes')
    price_subtotal = fields.Float('Subtotal', compute="_compute_price_subtotal")
    invoiced = fields.Boolean('Invoiced', copy=False, readonly=True)
    invoice_line_id = fields.Many2one(
        'account.invoice.line', 'Invoice Line', copy=False)

    @api.one
    @api.depends('price_unit', 'service_id', 'product_uom_qty', 'product_id', 'tax_id') #, 'service_id.invoice_method')
    def _compute_price_subtotal(self):
        taxes = self.tax_id.compute_all(self.price_unit, self.service_id.currency_id, self.product_uom_qty, self.product_id, self.service_id.partner_id)
        self.price_subtotal = taxes['total_excluded']

    @api.onchange('service_id', 'product_id', 'product_uom_qty')
    def onchange_product_id(self):
        """ On change of product it sets product quantity, tax, name, uom, price
        and price subtotal. """
        partner = self.service_id.partner_id

        if not self.product_id or not self.product_uom_qty:
            return
        if self.product_id:
            self.name = self.product_id.display_name
            self.product_uom = self.product_id.uom_id.id
        if partner and self.product_id:
            self.tax_id = partner.property_account_position_id.map_tax(self.product_id.taxes_id, self.product_id, partner).ids

class ServiceFee(models.Model):
    _name = 'service.fee'
    _description = 'Service Fees'
    # _inherits = {'work.fee': 'workfee_id'}

    name = fields.Text('Description', index=True, required=True)
    service_id = fields.Many2one(
        'service.order', 'Service Order Reference',
        index=True, ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', 'Jasa Service', required=True)
    product_uom_qty = fields.Float('Quantity', required=True, default=1.0)
    price_unit = fields.Float('Unit Price', required=True)
    product_uom = fields.Many2one('uom.uom', 'Product Unit of Measure', required=True)
    price_subtotal = fields.Float('Subtotal', compute='_compute_price_subtotal', store=True, digits=0)
    tax_id = fields.Many2many('account.tax', 'repair_fee_line_tax', 'repair_fee_line_id', 'tax_id', 'Taxes')
    invoice_line_id = fields.Many2one('account.invoice.line', 'Invoice Line', copy=False, readonly=True)
    invoiced = fields.Boolean('Invoiced', copy=False, readonly=True)

    @api.one
    @api.depends('price_unit', 'service_id', 'product_uom_qty', 'product_id')
    def _compute_price_subtotal(self):
        taxes = self.tax_id.compute_all(self.price_unit, self.service_id.currency_id, self.product_uom_qty, self.product_id, self.service_id.partner_id)
        self.price_subtotal = taxes['total_excluded']

    @api.onchange('service_id', 'product_id', 'product_uom_qty')
    def onchange_product_id(self):
        if not self.product_id:
            return

        partner = self.service_id.partner_id

        if partner and self.product_id:
            self.tax_id = partner.property_account_position_id.map_tax(self.product_id.taxes_id, self.product_id, partner).ids
        if self.product_id:
            self.name = self.product_id.display_name
            self.product_uom = self.product_id.uom_id.id
