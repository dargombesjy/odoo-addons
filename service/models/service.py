# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

class Partner(models.Model):
    _inherit = 'res.partner'

    # is_insurance = fields.Boolean('Insurance', default=False)
    partner_type = fields.Selection([
        ('internal', 'Internal'),
        ('customer', 'Customer'),
        ('vendor', 'Vendor'),
        ('insurance', 'Insurance')], string='Partner Type'
    )

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    service_id = fields.Many2one('service.order')

class StockMove(models.Model):
    _inherit = 'stock.move'

    service_id = fields.Many2one('service.order')

class ServiceOrder(models.Model):
    _name = 'service.order'
    _description = 'Service Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    def _get_default_currency_id(self):
        return self.env.user.company_id.currency_id.id

    @api.model
    def _default_stock_location(self):
        args = self.company_id and [('company_id', '=', self.company_id.id)] or []
        warehouse = self.env['stock.warehouse'].search(args, limit=1)
        if warehouse:
            return warehouse.lot_stock_id.id
        return False

    name = fields.Char(
        'Service reference',
        default=lambda self: self.env['ir.sequence'].next_by_code('service.order'),
        copy=False, required=True)
    # states={'confirmed': [('readonly', True)]})
    bill_type = fields.Selection([
        ('self', 'Bill to Customer'),
        ('claim', 'Bill to Insurance')], string="Billing Type", copy=False, required=True,
        default='claim')
    claim_reference = fields.Char('AMC')
    claim_id = fields.Char('Claim ID')
    policy_no = fields.Char('Policy No.')
    register_date = fields.Date('Register Date')
    planned_date = fields.Date('Planned Finish Date')
    finish_date = fields.Date('Actual Finish Date')
    equipment_id = fields.Many2one(
        'service.equipment', 'Equipment', copy=False, required=True, readonly=True,
        states={'draft': [('readonly', False)]})
    make = fields.Char('Manufacturer', compute='_compute_equipment')
    model = fields.Char('Model', compute='_compute_equipment')
    manuf_year = fields.Char('Year', compute='_compute_equipment')
    chassis_no = fields.Char('Chassis No.', compute='_compute_equipment')
    engine_no = fields.Char('Engine No.', compute='_compute_equipment')
    base_colour = fields.Char('Base Colour', compute='_compute_equipment')
    status_unit = fields.Selection([
        ('tla', 'TLA'),
        ('estimasi', 'Jasa Estimasi'),
        ('batal_klaim', 'Batal Klaim'),
        ('new', 'Unit In'),
        ('order_part', 'Order Part')], index=True)

    @api.one
    @api.depends('equipment_id')
    def _compute_equipment(self):
        details = self.equipment_id.get_details()
        self.make = details['make']
        self.model = details['model']
        self.manuf_year = details['manuf_year']
        self.chassis_no = details['chassis_no']
        self.engine_no = details['engine_no']
        self.base_colour = details['base_colour']

    partner_id = fields.Many2one(
        'res.partner', 'Customer', index=True)
    # domain=[('is_insurance', '=', False)])
    address_id = fields.Many2one(
        'res.partner', 'Delivery Address',
        domain="[('parent_id','=',partner_id)]",
        states={'confirmed': [('readonly', True)]})
    insurance_id = fields.Many2one(
        'res.partner', 'Insurance', index=True,
        domain=[('partner_type', '=', 'insurance')])
    # states={'confirmed': [('readonly', True)]})
    location_id = fields.Many2one(
        'stock.location', 'Stock Location',
        default=_default_stock_location,
        index=True, readonly=True, required=True)
        # help="This is the location where the product to repair is located.",
        # states={'draft': [('readonly', False)], 'confirmed': [('readonly', True)]})
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
    others_lines = fields.One2many(
        'service.other', 'service_id', copy=True)
    # readonly=True states={'draft': [('readonly', False)]})
    quotation_notes = fields.Text('Quotation Notes')
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env['res.company']._company_default_get('service.order'))
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
    invoiced = fields.Boolean('Invoiced', copy=False, readonly=True)
    repaired = fields.Boolean('Repaired', copy=False, readonly=True)
    amount_untaxed = fields.Float('Untaxed Amount', compute='_amount_untaxed', store=True)
    amount_tax = fields.Float('Taxes', compute='_amount_tax', store=True)
    amount_total = fields.Float('Total', compute='_amount_total', store=True)

    # ------ Operation --------- #
    work_stage = fields.Selection([
        ('bongkar', 'Pembongkaran'),
        ('ketok', 'Ketok'),
        ('dempul', 'Dempul'),
        ('epoxy', 'Epoxy'),
        ('cat', 'Pengecatan'),
        ('poles', 'Poles'),
        ('part_wait', 'Tunggu Part'),
        ('pasang', 'Pemasangan'),
        ('finishing', 'Finishing'),
        ('done', 'Selesai'),
        ('delivered', 'Delivered')], string='Stage', default="bongkar")
    cost_untaxed = fields.Float('Untaxed cost', compute='_cost_untaxed', store=True)
    cost_tax = fields.Float('Taxes', compute='_cost_tax', store=True)
    cost_total = fields.Float('Total cost', compute='_cost_total', store=True)
    purchased = fields.Boolean('PO Created', copy=False, readonly=True)
    purchase_id = fields.Many2one(
        'purchase.order', 'Purchase Order',
        copy=False, readonly=True, track_visibility="onchange")

    @api.onchange('equipment_id')
    def onchange_equipment_id(self):
        self.partner_id = self.equipment_id.partner_id.id

    @api.one
    @api.depends('operations.price_subtotal', 'invoice_method', 'fees_lines.price_subtotal', 'others_lines.price_subtotal')
    def _amount_untaxed(self):
        total = sum(operation.price_subtotal for operation in self.operations)
        total += sum(fee.price_subtotal for fee in self.fees_lines)
        total += sum(other.price_subtotal for other in self.others_lines)
        self.amount_untaxed = total

    @api.one
    @api.depends('operations.price_unit', 'operations.product_uom_qty', 'operations.product_id',
                 'fees_lines.price_unit', 'fees_lines.product_uom_qty', 'fees_lines.product_id',
                 'others_lines.price_unit', 'others_lines.product_uom_qty', 'others_lines.product_id',
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
        for other in self.others_lines:
            if other.tax_id:
                tax_calculate = other.tax_id.compute_all(other.price_unit, self.currency_id, other.product_uom_qty, other.product_id, self.partner_id)
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

    @api.onchange('partner_id', 'insurance_id')
    def onchange_partner_id(self):
        if not self.partner_id:
            self.address_id = False
            self.partner_invoice_id = False
            # self.pricelist_id = self.env['product.pricelist'].search([], limit=1).id
        else:
            if self.bill_type == 'self':
                addresses = self.partner_id.address_get(['delivery', 'invoice', 'contact'])
            else:
                addresses = self.insurance_id.address_get(['delivery', 'invoice', 'contact'])
            self.address_id = addresses['delivery'] or addresses['contact']
            self.partner_invoice_id = addresses['invoice']
            # self.pricelist_id = self.partner_id.property_product_pricelist.id

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

    def action_service_invoice_create(self):
        for service in self:
            service.action_invoice_create()
            if service.invoice_method == 'b4repair':
                service.action_service_ready()
            elif service.invoice_method == 'after_repair':
                service.write({'state': 'done'})
        return True

    def action_service_ready(self):
        self.mapped('operations').write({'state': 'confirmed'})
        return self.write({'state': 'ready'})

    @api.multi
    def action_invoice_create(self, group=False):
        """ Creates invoice(s) for service order
        @param group: It is set to true when group invoice is to be generated.
        @return: Invoice Ids.
        """
        res = dict.fromkeys(self.ids, False)
        invoices_group = {}
        InvoiceLine = self.env['account.invoice.line']
        Invoice = self.env['account.invoice']
        for service in self.filtered(lambda service: service.state not in ('draft', 'cancel') and not service.invoice_id):
            if not service.partner_id.id and not service.partner_invoice_id.id:
                raise UserError(_('You have to select an invoice address in the service form.'))
            comment = service.quotation_notes
            if service.invoice_method != 'none':
                if group and service.partner_invoice_id.id in invoices_group:
                    invoice = invoices_group[service.partner_invoice_id.id]
                    invoice.write({
                        'name': invoice.name + ', ' + service.name,
                        'origin': invoice.origin + ', ' + service.name,
                        'comment': (comment and (invoice.comment and invoice.comment + "\n" + comment or comment)) or (invoice.comment and invoice.comment or ''),
                    })
                else:
                    # if not service.partner_id.property_account_receivable_id:
                    if not service.partner_invoice_id.property_account_receivable_id:
                        raise UserError(_('No sccount defined for partner "%s%"' % service.partner_invoice_id.name))
                        # raise UserError(_('No account defined for parner "%s%"') % service.partner_id.name)
                    invoice = Invoice.create({
                        'name': service.name,
                        'origin': service.name,
                        'type': 'out_invoice',
                        # 'account_id': service.partner_id.property_account_receivable_id.id,
                        'account_id': service.partner_invoice_id.property_account_receivable_id.id,
                        # 'partner_id': service.partner_invoice_id.id or service.partner_id.id,
                        'partner_id': service.partner_invoice_id.id,
                        'currency_id': service.currency_id.id,
                        # 'comment': service.quotation_notes,
                        # 'fiscal_position_id': service.partner_id.property_account_position_id
                        'fiscal_position_id': service.partner_invoice_id.property_account_position_id
                    })
                    invoices_group[service.partner_invoice_id.id] = invoice

                service.write({'invoiced': True, 'invoice_id': invoice.id})

                for operation in service.operations:
                    if group:
                        name = service.name + '-' + operation.name
                    else:
                        name = operation.name

                    if operation.product_id.property_account_income_id:
                        account_id = operation.property_account_income_id.id
                    elif operation.product_id.categ_id.property_account_income_categ_id:
                        account_id = operation.product_id.categ_id.property_account_income_categ_id.id
                    else:
                        raise UserError(_('No account defined for product "%s%".') % operation.product_id.name)

                    invoice_line = InvoiceLine.create({
                        'invoice_id': invoice.id,
                        'name': name,
                        'origin': service.name,
                        'account_id': account_id,
                        'quantity': operation.product_uom_qty,
                        'invoice_line_tax_ids': [(6, 0, [x.id for x in operation.tax_id])],
                        'uom_id': operation.product_uom.id,
                        'price_unit': operation.price_unit,
                        'price_subtotal': operation.product_uom_qty * operation.price_unit,
                        'product_id': operation.product_id and operation.product_id.id or False
                    })
                    operation.write({'invoiced': True, 'invoice_line_id': invoice_line.id})

                for fee in service.fees_lines:
                    if group:
                        name = service.name + '-' + fee.name
                    else:
                        name = fee.name
                    if not fee.product_id:
                        raise UserError(_('No product defined on fees.'))

                    if fee.product_id.property_account_income_id:
                        account_id = fee.property_account_income_id.id
                    elif fee.product_id.categ_id.property_account_income_categ_id:
                        account_id = fee.product_id.categ_id.property_account_income_categ_id.id
                    else:
                        raise UserError(_('No account defined for product "%s%".') % fee.product_id.name)

                    invoice_line = InvoiceLine.create({
                        'invoice_id': invoice.id,
                        'name': name,
                        'origin': service.name,
                        'account_id': account_id,
                        'quantity': fee.product_uom_qty,
                        'invoice_line_tax_ids': [(6, 0, [x.id for x in fee.tax_id])],
                        'uom_id': fee.product_uom.id,
                        'product_id': fee.product_id and fee.product_id.id or False,
                        'price_unit': fee.price_unit,
                        'price_subtotal': fee.product_uom_qty * fee.price_unit
                    })
                    fee.write({'invoiced': True, 'invoice_line_id': invoice_line.id})

                invoice.compute_taxes()
                res[service.id] = invoice.id
        return res

    @api.multi
    def action_created_invoice(self):
        self.ensure_one()
        return {
            'name': _('Invoice created'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account_invoice',
            'view_id': self.env.ref('account.invoice_form').id,
            'target': 'current',
            'res_id': self.invoice_id.id,
        }

class ServiceLine(models.Model):
    _name = 'service.line'
    _description = 'Service Line (Part)'

    name = fields.Text('Description')
    part_number = fields.Char('Part Number')
    service_id = fields.Many2one(
        'service.order', 'Service Order reference',
        index=True, ondelete='cascade')
    # type = fields.Selection([
    #     ('add', "Add"),
    #     ('remove', "Remove")], 'Type', required=True)
    supply_type = fields.Selection([
        ('self', 'Self Supply'),
        ('customer', 'Customer Supply'),
        ('vendor', 'Vendor Supply')], 'Supply Type', index=True, required=True,
        default='vendor')
    product_id = fields.Many2one('product.product', 'Sparepart', required=True)
    product_uom_qty = fields.Float('Quantity', default=1.0, required=True)
    product_uom = fields.Many2one(
        'uom.uom', 'Product Unit od Measure')
    price_unit = fields.Float('Unit Price', required=True)
    # price_accepted = fields.Float('Accepted Price')
    tax_id = fields.Many2many(
        'account.tax', 'service_operation_line_tax', 'service_operation_line_id', 'tax_id', 'Taxes')
    price_subtotal = fields.Float('Subtotal', compute="_compute_price_subtotal")
    invoiced = fields.Boolean('Invoiced', copy=False, readonly=True)
    rejected = fields.Boolean('Repaired', copy=False, readonly=True)
    invoice_line_id = fields.Many2one(
        'account.invoice.line', 'Invoice Line', copy=False)

    # Production line ---- #
    received = fields.Boolean('Received', copy=False)
    location_id = fields.Many2one(
        'stock.location', 'Source Location', index=True)
    location_dest_id = fields.Many2one(
        'stock.location', 'Dest. Location', index=True)
    move_id = fields.Many2one(
        'stock.move', 'Inventory Move', copy=False, readonly=True)
    lot_id = fields.Many2one('stock.production.lot', 'Lot/Serial')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], 'Status', default='draft',
        copy=False, readonly=True, required=True,
        help='The status of a repair line is set automatically to the one of the linked repair order.')
    cost_unit = fields.Float('Unit Cost', required=True, default=0.0)
    cost_tax_id = fields.Many2many(
        'account.tax', 'service_operation_line_tax', 'service_operation_line_id', 'tax_id', 'Taxes')
    cost_subtotal = fields.Float('Subtotal', compute='_compute_cost_subtotal', store=True, digits=0)
    purchased = fields.Boolean('Purchased', copy=False, required=True)
    purchase_line_id = fields.Many2one(
        'purchase.order.line', 'Purchase Line', copy=False)
    vendor_id = fields.Many2one('res.partner', 'Vendor', copy=False)

    @api.one
    @api.depends('price_unit', 'service_id', 'product_uom_qty', 'product_id', 'tax_id') #, 'service_id.invoice_method')
    def _compute_price_subtotal(self):
        taxes = self.tax_id.compute_all(self.price_unit, self.service_id.currency_id, self.product_uom_qty, self.product_id, self.service_id.partner_id)
        self.price_subtotal = taxes['total_excluded']

    @api.onchange('suppy_type', 'service_id')
    def onchange_operation_type(self):
        """ On change of operation type it sets source location, destination location
        and to invoice field.
        @param product: Changed operation type.
        @param guarantee_limit: Guarantee limit of current record.
        @return: Dictionary of values.
        """
        self.onchange_product_id()
        args = self.service_id.company_id and [('company_id', '=', self.service_id.company_id.id)] or []
        warehouse = self.env['stock.warehouse'].search(args, limit=1)
        self.location_id = warehouse.lot_stock_id
        self.location_dest_id = self.env['stock.location'].search([('usage', '=', 'customer')], limit=1).id
        # else:
        #     self.price_unit = 0.0
        #     self.tax_id = False
        #     self.location_id = self.env['stock.location'].search([('usage', '=', 'production')], limit=1).id
        #     self.location_dest_id = self.env['stock.location'].search([('scrap_location', '=', True)], limit=1).id

    @api.onchange('service_id', 'product_id', 'product_uom_qty')
    def onchange_product_id(self):
        """ On change of product it sets product quantity, tax, name, uom, price
        and price subtotal. """
        partner = self.service_id.partner_id
        self.lot_id = False

        if not self.product_id or not self.product_uom_qty:
            return
        if self.product_id:
            self.name = self.product_id.name
            self.part_number = self.product_id.default_code
            self.product_uom = self.product_id.uom_id.id
        if partner and self.product_id:
            self.tax_id = partner.property_account_position_id.map_tax(self.product_id.taxes_id, self.product_id, partner).ids

class ServiceFee(models.Model):
    _name = 'service.fee'
    _description = 'Service Fees'
    # _inherits = {'work.fee': 'workfee_id'}

    name = fields.Text('Description', index=True)
    fee_code = fields.Char('Service Code')
    service_id = fields.Many2one(
        'service.order', 'Service Order Reference',
        index=True, ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', 'Service Fee', required=True)
    product_uom_qty = fields.Float('Quantity', required=True, default=1.0)
    price_unit = fields.Float('Unit Price', required=True)
    # price_accepted = fields.Float('Accepted Price')
    product_uom = fields.Many2one('uom.uom', 'Product Unit of Measure', required=True)
    price_subtotal = fields.Float('Subtotal', compute='_compute_price_subtotal', store=True, digits=0)
    tax_id = fields.Many2many('account.tax', 'service_fee_line_tax', 'service_fee_line_id', 'tax_id', 'Taxes')
    invoice_line_id = fields.Many2one('account.invoice.line', 'Invoice Line', copy=False, readonly=True)
    invoiced = fields.Boolean('Invoiced', copy=False, readonly=True)
    rejected = fields.Boolean('Repaired', copy=False, readonly=True)

    # ------ Production ------ #
    cost_unit = fields.Float('Unit Cost', required=True, default=0.0)
    cost_tax_id = fields.Many2many(
        'account.tax', 'service_fee_line_tax', 'service_fee_line_id', 'tax_id', 'Taxes')
    cost_subtotal = fields.Float('Subtotal', compute='_compute_cost_subtotal', store=True, digits=0)
    purchased = fields.Boolean('Purchased', copy=False, required=True)
    purchase_line_id = fields.Many2one(
        'purchase.order.line', 'Purchase Line', copy=False)
    vendor_id = fields.Many2one('res.partner', 'Vendor', copy=False)

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
            self.name = self.product_id.name
            self.fee_code = self.product_id.default_code
            self.product_uom = self.product_id.uom_id.id

class ServiceOther(models.Model):
    _name = 'service.other'
    _description = 'Service Others lines'

    name = fields.Text('Description')
    other_code = fields.Char('Item Code')
    service_id = fields.Many2one(
        'service.order', 'Service Order Reference',
        index=True, ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', 'Jasa Other', required=True)
    product_uom_qty = fields.Float('Quantity', required=True, default=1.0)
    price_unit = fields.Float('Unit Price', required=True)
    # price_accepted = fields.Float('Accepted Price')
    product_uom = fields.Many2one('uom.uom', 'Product Unit of Measure', required=True)
    price_subtotal = fields.Float('Subtotal', compute='_compute_price_subtotal', store=True, digits=0)
    tax_id = fields.Many2many('account.tax', 'service_others_line_tax', 'service_others_line_id', 'tax_id', 'Taxes')
    invoice_line_id = fields.Many2one('account.invoice.line', 'Invoice Line', copy=False, readonly=True)
    invoiced = fields.Boolean('Invoiced', copy=False, readonly=True)
    rejected = fields.Boolean('Repaired', copy=False, readonly=True)

    # ------ Production ------ #
    cost_unit = fields.Float('Unit Cost', required=True, default=0.0)
    cost_tax_id = fields.Many2many(
        'account.tax', 'service_others_cost_tax', 'service_others_line_id', 'tax_id', 'Taxes')
    cost_subtotal = fields.Float('Subtotal', compute='_compute_cost_subtotal', store=True, digits=0)
    purchased = fields.Boolean('Purchased', copy=False, required=True)
    purchase_line_id = fields.Many2one(
        'purchase.order.line', 'Purchase Line', copy=False)
    vendor_id = fields.Many2one('res.partner', 'Vendor', copy=False)

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
            self.name = self.product_id.name
            self.other_code = self.product_id.default_code
            self.product_uom = self.product_id.uom_id.id

class ServiceConsumable(models.Model):
    _name = 'service.consumable'
    _description = 'Consumable lines'

    name = fields.Text('Description')
    service_id = fields.Many2one(
        'service.order', 'Service Order Reference',
        index=True, ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', 'Jasa Service', required=True)
    product_uom_qty = fields.Float('Quantity', required=True, default=1.0)
    product_uom = fields.Many2one('uom.uom', 'Product Unit of Measure', required=True)
    cost_unit = fields.Float('Unit Cost', required=True, default=0.0)
    cost_tax_id = fields.Many2many(
        'account.tax', 'service_consumable_line_tax', 'service_consumable_line_id', 'tax_id', 'Taxes')
    cost_subtotal = fields.Float('Subtotal', compute='_compute_cost_subtotal', store=True, digits=0)

    @api.onchange('service_id', 'product_id', 'product_uom_qty')
    def onchange_product_id(self):
        if not self.product_id:
            return

        # partner = self.service_id.partner_id
        #
        # if partner and self.product_id:
        #     self.tax_id = partner.property_account_position_id.map_tax(self.product_id.taxes_id, self.product_id, partner).ids
        if self.product_id:
            self.name = self.product_id.name
            # self.other_code = self.product_id.default_code
            self.product_uom = self.product_id.uom_id.id
