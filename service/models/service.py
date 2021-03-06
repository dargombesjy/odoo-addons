# -*- coding: utf-8 -*-
import xlsxwriter
import base64
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from num2words import num2words
# from html5lib._ihatexml import digit

SUPPLY_TYPES = [
        ('self', 'Self Supply'),
        ('customer', 'Customer Supply'),
        ('vendor', 'Vendor Supply')]


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    service_id = fields.Many2one('service.order')
    eq_name = fields.Char('License Plate')
    eq_model = fields.Char('Model')
    receiver = fields.Char('Receiver')
    received_date = fields.Date('Received Date')
    vendor_id = fields.Many2one(
        'res.partner', 'Vendor', index=True, readonly=True,
        states={'draft': [('readonly', False)]})

    @api.multi
    def action_confirm(self):
        if self.mapped('move_lines').filtered(lambda move: not move.product_id):
            raise UserError(_('All items must have Product ID'))

        self.mapped('package_level_ids').filtered(lambda pl: pl.state == 'draft' and not pl.move_ids)._generate_moves()
        # call `_action_confirm` on every draft move
        self.mapped('move_lines')\
            .filtered(lambda move: move.state == 'draft')\
            ._action_confirm()
        # call `_action_assign` on every confirmed move which location_id bypasses the reservation
        self.filtered(lambda picking: picking.location_id.usage in ('supplier', 'inventory', 'production') and picking.state == 'confirmed')\
            .mapped('move_lines')._action_assign()
        return True

    @api.multi
    def action_assign(self):
        """ Check availability of picking moves.
        This has the effect of changing the state and reserve quants on available moves, and may
        also impact the state of the picking as it is computed based on move's states.
        @return: True
        """
        move_supply = self.env['stock.move']
        for move in self.move_lines:
            if move.product_category == 'Sparepart' and move.vendor_id and move.vendor_qty > 0:
                total_received = move.vendor_received + move.vendor_qty
                move_qty = 0
                if total_received <= move.product_uom_qty:
                    move_qty = move.vendor_qty
                else:
                    if move.vendor_received < move.product_uom_qty:
                        move_qty = move.product_uom_qty - move.vendor_received
                        total_received = move.product_uom_qty

                if move_qty > 0:
                    supply = move_supply.create({
                        'name': move.name,
                        'date': move.vendor_date,
                        'product_id': move.product_id.id, #operation.product_id.id,
                        'product_uom_qty': move.product_uom_qty, #operation.product_uom_qty,
                        'product_uom': move.product_uom.id, #operation.product_uom.id,
                        'partner_id': move.picking_id.partner_id.id, #repair.address_id.id,
                        'location_id': 8, #operation.location_id.id,
                        'location_dest_id': move.location_id.id, #operation.location_dest_id.id,
                        'move_line_ids': [(0, 0, {'product_id': move.product_id.id, #operation.product_id.id,
                                                  #'lot_id': move.lot_id, #operation.lot_id.id,
                                                  'product_uom_qty': move.product_uom_qty,  # bypass reservation here
                                                  'product_uom_id': move.product_uom.id, #operation.product_uom.id,
                                                  'qty_done': move_qty, #operation.product_uom_qty,
                                                  'package_id': False,
                                                  'result_package_id': False,
                                                  #'owner_id': #owner_id,
                                                  'location_id': 8, #move.location_id, #operation.location_id.id, #TODO: owner stuff
                                                  'location_dest_id': move.location_id.id })], #operation.location_dest_id.id,})],
                        'origin': move.service_id.id, #repair.id,
                        'service_id': move.service_id.id, #repair.id,
                        'service_line_id': move.service_line_id, #repair.name,
                    })
                    move.write({'vendor_received': total_received})
                    supply._action_done()

        self.filtered(lambda picking: picking.state == 'draft').action_confirm()
        moves = self.mapped('move_lines').filtered(lambda move: move.state not in ('draft', 'cancel', 'done'))
        if not moves:
            raise UserError(_('Nothing to check the availability for.'))
        # If a package level is done when confirmed its location can be different than where it will be reserved.
        # So we remove the move lines created when confirmed to set quantity done to the new reserved ones.
        package_level_done = self.mapped('package_level_ids').filtered(lambda pl: pl.is_done and pl.state == 'confirmed')
        package_level_done.write({'is_done': False})
        moves._action_assign()
        package_level_done.write({'is_done': True})
        return True

class StockMove(models.Model):
    _inherit = 'stock.move'

    service_id = fields.Many2one('service.order')
    service_line_id = fields.Integer('Line Id')
    product_id = fields.Many2one(
        'product.product', 'Product',
        domain=[('type', 'in', ['product', 'consu'])], index=True, required=False)
    product_category = fields.Char('Product Category')
    supply_type = fields.Selection(SUPPLY_TYPES, 'Supply Type')
    vendor_id = fields.Many2one('res.partner', 'Vendor', index=True)
    vendor_qty = fields.Float('Qty. Terima')
    vendor_date = fields.Date('Tgl. Terima')
    vendor_received = fields.Float('Recv')
    receiver = fields.Char('Penerima')
    received_date = fields.Date('Tgl. Ambil')
    
    def action_set_draft(self):
        return self.write({'state': 'draft'})

    @api.constrains('product_uom')
    def _check_uom(self):
        moves_error = self.filtered(lambda move: move.product_id.uom_id.category_id != move.product_uom.category_id)
        sparepart = self.filtered(lambda move: move.product_category == 'Sparepart')
        if sparepart:
            moves_error = False
        # if self.product_category == 'Sparepart' and self.state == 'draft':
        #     moves_error = False
        if moves_error:
            user_warning = _('You cannot perform the move because the unit of measure has a different category as the product unit of measure.')
            for move in moves_error:
                user_warning += _('\n\n%s --> Product UoM is %s (%s) - Move UoM is %s (%s)') % (move.product_id.display_name, move.product_id.uom_id.name, move.product_id.uom_id.category_id.name, move.product_uom.name, move.product_uom.category_id.name)
            user_warning += _('\n\nBlocking: %s') % ' ,'.join(moves_error.mapped('name'))
            raise UserError(user_warning)

    @api.one
    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_product_qty(self):
        rounding_method = self._context.get('rounding_method', 'UP')
        if not self.product_category == 'Sparepart':
            self.product_qty = self.product_uom._compute_quantity(self.product_uom_qty, self.product_id.uom_id, rounding_method=rounding_method)
        else:
            if self.state == 'draft':
                self.product_qty = self.product_uom._compute_quantity(self.product_uom_qty, self.product_uom, rounding_method=rounding_method)

    def _action_confirm(self, merge=True, merge_into=False):
        """ Confirms stock move or put it in waiting if it's linked to another move.
        :param: merge: According to this boolean, a newly confirmed move will be merged
        in another move of the same picking sharing its characteristics.
        """
        move_create_proc = self.env['stock.move']
        move_to_confirm = self.env['stock.move']
        move_waiting = self.env['stock.move']

        to_assign = {}
        for move in self:
            if move.service_id:
                if move.product_category == 'Sparepart' or move.product_category == 'Bahan':
                    service_line = move.env['service.line'].search([('id', '=', move.service_line_id)], limit=1)
                else:
                    service_line = move.env['service.consumable'].search([('id', '=', move.service_line_id)], limit=1)
                service_line.write({'received': True})

            # if the move is preceeded, then it's waiting (if preceeding move is done, then action_assign has been called already and its state is already available)
            if move.move_orig_ids:
                move_waiting |= move
            else:
                if move.procure_method == 'make_to_order':
                    move_create_proc |= move
                else:
                    move_to_confirm |= move
            if move._should_be_assigned():
                key = (move.group_id.id, move.location_id.id, move.location_dest_id.id)
                if key not in to_assign:
                    to_assign[key] = self.env['stock.move']
                to_assign[key] |= move

        # create procurements for make to order moves
        for move in move_create_proc:
            values = move._prepare_procurement_values()
            origin = (move.group_id and move.group_id.name or (move.origin or move.picking_id.name or "/"))
            self.env['procurement.group'].run(move.product_id, move.product_uom_qty, move.product_uom, move.location_id, move.rule_id and move.rule_id.name or "/", origin,
                                              values)

        move_to_confirm.write({'state': 'confirmed'})
        (move_waiting | move_create_proc).write({'state': 'waiting'})

        # assign picking in batch for all confirmed move that share the same details
        for moves in to_assign.values():
            moves._assign_picking()
        self._push_apply()
        if merge:
            return self._merge_moves(merge_into=merge_into)
        return self

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_category == 'Sparepart':
            service_line = self.env['service.line'].search([('id', '=', self.service_line_id)], limit=1)
            cost = service_line.cost_unit
            if service_line.supply_type == 'self' and cost == 0:
                cost = self.product_id.standard_price
            service_line.write({'product_id': self.product_id.id, 'cost_unit': cost})
            if not self.supply_type:
                self.supply_type = service_line.supply_type

        product = self.product_id.with_context(lang=self.partner_id.lang or self.env.user.lang)
        self.product_uom = product.uom_id.id
        return {'domain': {'product_uom': [('category_id', '=', product.uom_id.category_id.id)]}}

    @api.multi
    def write(self, values):
        lines = super(StockMove, self).write(values)
        for line in self:
            if line.product_id and line.supply_type == 'self':
                if line.product_id.standard_price == 0:
                    raise UserError(_('Product "%s" belum memiliki harga standar') % line.product_id.name)
        return lines

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    # service_line_id = fields.Many2one('service.line')
    product_alias = fields.Char('Product Alias')

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
        copy=False, required=True, states={'draft': [('readonly', False)]})
    bill_type = fields.Selection([
        ('self', 'Bill to Customer'),
        ('claim', 'Bill to Insurance')], string="Billing Type", copy=False, required=True,
        default='self')
    claim_reference = fields.Char('AMC')
    claim_id = fields.Char('Claim ID')
    policy_no = fields.Char('Policy No.')
    register_date = fields.Date('Register Date', required=True, default=fields.Date.today)
    received_date = fields.Date('Doc. Receive Date', default=fields.Date.today)
    planned_date = fields.Date('Planned Finish Date') # , required=True)
    finish_date = fields.Date('Actual Finish Date')
    equipment_id = fields.Many2one(
        'service.equipment', 'Equipment', copy=False, required=True,
        readonly=True, states={'draft': [('readonly', False)]})
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
        ('order_part', 'Order Part'),
        ('derek', 'Derek'),
        ('pick_up', 'Pick Up')], index=True, readonly=True,
        states={'draft': [('readonly', False)]})

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

    @api.one
    @api.depends('partner_id')
    def _compute_partner(self):
        self.partner_type = self.partner_id.company_type

    partner_id = fields.Many2one(
        'res.partner', 'Customer', index=True, readonly=True,
        states={'draft': [('readonly', False)]})
    partner_type = fields.Char('Customer Type', compute='_compute_partner', store=True)
    service_advisor = fields.Char('Service Advisor')
    address_id = fields.Many2one(
        'res.partner', 'Delivery Address', index=True, readonly=True,
        states={'draft': [('readonly', False)]})
    insurance_id = fields.Many2one(
        'res.partner', 'Insurance', index=True, readonly=True,
        states={'draft': [('readonly', False)]})
    location_id = fields.Many2one(
        'stock.location', 'Stock Location',
        default=_default_stock_location,
        index=True, required=True, readonly=True, states={'draft': [('readonly', False)]})
    # help="This is the location where the product to repair is located.",
    # states={'draft': [('readonly', False)], 'confirmed': [('readonly', True)]})
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('cancel', 'Cancelled'),
        ('confirmed', 'Confirmed'),
        ('under_repair', 'Under Repair'),
        ('ready', 'Repair Done'),
        ('2binvoiced', 'To be Invoiced'),
        ('invoice_except', 'Invoice Exception'),
        ('done', 'Closed')],
        string='Status', copy=False, default='draft', readonly=True,
        track_visibility='onchange',
        help="* The \'Draft\' status is used when a user is encoding a new and unconfirmed repair order.\n"
             "* The \'Confirmed\' status is used when a user confirms the repair order.\n"
             "* The \'Ready to Repair\' status is used to start to repairing, user can start repairing only after repair order is confirmed.\n"
             "* The \'To be Invoiced\' status is used to generate the invoice before or after repairing done.\n"
             "* The \'Done\' status is set when repairing is completed.\n"
             "* The \'Cancelled\' status is used when user cancel repair order.")
    has_confirmed = fields.Boolean('Has Confirmed')
    operations = fields.One2many(
        'service.line', 'service_id', 'Part', copy=True)
        # readonly=True, states={'draft': [('readonly', False)], 'confirmed': [('readonly', False)]})
    fees_lines = fields.One2many(
        'service.fee', 'service_id', copy=True)
        # readonly=True, states={'draft': [('readonly', False)], 'confirmed': [('readonly', False)]})
    others_lines = fields.One2many(
        'service.other', 'service_id', copy=True)
        # readonly=True, states={'draft': [('readonly', False)], 'confirmed': [('readonly', False)]})
    consumable_lines = fields.One2many(
        'service.consumable', 'service_id', copy=True)
    quotation_notes = fields.Text('Quotation Notes')
    company_id = fields.Many2one(
        'res.company', 'Company', readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: self.env['res.company']._company_default_get('service.order'))
    partner_invoice_id = fields.Many2one('res.partner', 'Invoicing Address')  # , readonly=True, states={'draft': [('readonly', False)]})
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
    invoice_or_id = fields.Many2one(
        'account.invoice', 'Invoice OR',
        copy=False, readonly=True, track_visibility="onchange")
    invoiced = fields.Boolean('Invoiced', copy=False, readonly=True)
    repaired = fields.Boolean('Repaired', copy=False, readonly=True)
    amount_sparepart = fields.Float('Pend. Sparepart', compute='_amount_untaxed', store=True, digits=(12,0))
    amount_jasa = fields.Float('Pend. Jasa', compute='_amount_untaxed', store=True, digits=(12,0))
    amount_others = fields.Float('Pend. Others', compute='_amount_untaxed', store=True, digits=(12,0))
    amount_untaxed = fields.Float('Untaxed Amount', compute='_amount_untaxed', store=True, digits=(12,0))
    amount_tax_sparepart = fields.Float('Sparepart Taxes', compute='_amount_tax', store=True, digits=(12,0))
    amount_tax_jasa = fields.Float('Jasa Taxes', compute='_amount_tax', store=True, digits=(12,0))
    amount_tax_others = fields.Float('Others Taxes', compute='_amount_tax', store=True, digits=(12,0))
    amount_tax = fields.Float('Taxes', compute='_amount_tax', store=True, digits=(12,0))
    amount_own_risk = fields.Float('Own Risk', compute='_amount_untaxed', store=True, digits=(12,0))
    amount_total = fields.Float('Total', compute='_amount_total', store=True, digits=(12,0))
    cost_operations = fields.Float('Cost Sparepart', compute='_cost_untaxed', store=True, digits=(12,0))
    cost_fees = fields.Float('Cost Jasa', compute='_cost_untaxed', store=True, digits=(12,0))
    cost_others = fields.Float('Cost Others', compute='_cost_untaxed', store=True, digit=(12,0))
    cost_bahan = fields.Float('Cost Bahan', compute='_cost_untaxed', store=True, digits=(12,0))
    cost_total = fields.Float('Cost', compute='_cost_untaxed', store=True, digits=(12,0))
    own_risk_invoiced = fields.Boolean('Own Risk invoiced')
    print_tax = fields.Boolean('Print Tax?')

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
    purchased = fields.Boolean('PO Created', copy=False, readonly=True)
    # purchase_id = fields.Many2one(
    #     'purchase.order', 'Purchase Order',
    #     copy=False, readonly=True, track_visibility="onchange")
    purchase_ids = fields.Many2many('purchase.order', 'service_order_po',
        'service_order_id', 'purchase_order_id', 'Purchase Orders')
    vendor_ids = fields.Many2many('res.partner', 'service_order_vendor',
        'service_order_id', 'vendor_id', 'Vendors')
#     sparepart_picking_id = fields.Many2one('stock.picking', 'Sparepart Pick ID',
#         readonly=True, copy=False, index=True)
#     consumable_picking_id = fields.Many2one('stock.picking', 'Consumable Pick ID',
#         readonly=True, copy=False, index=True)
#     items_ok = fields.Boolean('Materials received',  compute="_compute_received_flag", store=True)

    @api.onchange('equipment_id')
    def onchange_equipment_id(self):
        self.partner_id = self.equipment_id.partner_id.id

    @api.one
    @api.depends('operations.price_subtotal', 'invoice_method', 'fees_lines.price_subtotal', 'others_lines.price_subtotal')
    def _amount_untaxed(self):
        sparepart_sum = 0
        fee_sum = 0
        other_sum = 0
        for line in self.operations:
            if line.supply_type == 'self' and line.approved:
                sparepart_sum += line.price_subtotal
#         sparepart_sum = sum(operation.price_subtotal for operation in self.operations if operation.approved)
        for fee in self.fees_lines:
            if fee.approved:
                fee_sum += fee.price_subtotal
#         fee_sum = sum(fee.price_subtotal for fee in self.fees_lines if fee.approved)
        
        for other in self.others_lines:
            if other.product_id.name == 'Own Risk':
                self.amount_own_risk = other.price_subtotal
            else:
#                 if other.approved:
                other_sum = other.price_subtotal
                    
        self.amount_sparepart = sparepart_sum
        self.amount_jasa = fee_sum
        self.amount_others = other_sum
        self.amount_untaxed = sparepart_sum + fee_sum + other_sum

    @api.one
    @api.depends('operations.price_unit', 'operations.product_uom_qty', 'operations.product_id',
                 'fees_lines.price_unit', 'fees_lines.product_uom_qty', 'fees_lines.product_id',
                 'others_lines.price_unit', 'others_lines.product_uom_qty', 'others_lines.product_id',
                 'currency_id', 'partner_id')
    def _amount_tax(self):
        val = 0.0
        sparepart_tax = 0
        fee_tax = 0
        other_tax = 0
        for operation in self.operations:
            if operation.approved and operation.supply_type == 'self':
                if operation.tax_id:
                    tax_calculate = operation.tax_id.compute_all(operation.price_unit, self.currency_id, operation.product_uom_qty, operation.product_id, self.partner_id)
                    for c in tax_calculate['taxes']:
                        sparepart_tax += c['amount']
                        val += c['amount']
        for fee in self.fees_lines:
            if fee.approved:
                if fee.tax_id:
                    tax_calculate = fee.tax_id.compute_all(fee.price_unit, self.currency_id, fee.product_uom_qty, fee.product_id, self.partner_id)
                    for c in tax_calculate['taxes']:
                        fee_tax += c['amount']
                        val += c['amount']
        for other in self.others_lines:
            if other.product_id.name != 'Own Risk' and other.tax_id:
                tax_calculate = other.tax_id.compute_all(other.price_unit, self.currency_id, other.product_uom_qty, other.product_id, self.partner_id)
                for c in tax_calculate['taxes']:
                    other_tax = c['amount']
                    val += c['amount']
        
        self.amount_tax_sparepart = sparepart_tax
        self.amount_tax_jasa = fee_tax
        self.amount_tax_others = other_tax
        self.amount_tax = val

    @api.one
    @api.depends('amount_untaxed', 'amount_tax')
    def _amount_total(self):
        self.amount_total = self.currency_id.round(self.amount_untaxed + self.amount_tax)

    @api.one
    @api.depends('operations.cost_subtotal', 'invoice_method', 'fees_lines.cost_subtotal',
                 'others_lines.cost_subtotal', 'consumable_lines.cost_subtotal')
    def _cost_untaxed(self):
        cost_part = sum(operation.cost_subtotal for operation in self.operations)
        cost_jasa = sum(fee.cost_subtotal for fee in self.fees_lines)
        cost_others = 0
        for other in self.others_lines:
            if other.product_id.name != 'Own Risk':
                cost_others += other.cost_subtotal
        cost_bahan = sum(consumable.cost_subtotal for consumable in self.consumable_lines)
        self.cost_operations = cost_part
        self.cost_fees = cost_jasa
        self.cost_others = cost_others
        self.cost_bahan = cost_bahan
        self.cost_total = cost_part + cost_jasa + cost_others + cost_bahan

    _sql_constraints = [
        ('name', 'unique (name)', 'The name of the Service Order must be unique!')
    ]

    @api.onchange('partner_id', 'insurance_id')
    def onchange_partner_id(self):
        partner_addresses = self.partner_id.address_get(['delivery', 'invoice', 'contact'])
        self.address_id = partner_addresses['delivery'] or partner_addresses['contact']
        if not self.partner_id:
            self.address_id = False
            self.partner_invoice_id = False
            # self.pricelist_id = self.env['product.pricelist'].search([], limit=1).id
        else:
            if self.bill_type == 'self':
                addresses = self.partner_id.address_get(['delivery', 'invoice', 'contact'])
            else:
                addresses = self.insurance_id.address_get(['delivery', 'invoice', 'contact'])
            self.partner_invoice_id = addresses['invoice']
            self.pricelist_id = self.partner_id.property_product_pricelist.id

    @api.multi
    def button_dummy(self):
        # TDE FIXME: this button is very interesting
        return True

    @api.multi
    def action_service_confirm(self):
        if self.filtered(lambda service: service.state != 'draft'):
            raise UserError(_("Only draft repair can be confirmed."))
        if self.bill_type == 'claim':
            if not self.insurance_id:
                raise UserError(_("For Claim, Insurance must be filled"))
        before_repair = self.filtered(lambda service: service.invoice_method == 'b4repair')
        before_repair.write({'state': '2binvoiced'})
        to_confirm = self - before_repair
        if self.has_confirmed:
            to_confirm.write({'state': 'under_repair'})
        else:
            to_confirm_operations = to_confirm.mapped('operations')
            to_confirm_operations.write({'state': 'confirmed'})
            to_confirm.write({'state': 'confirmed', 'has_confirmed': True})
        return True

    @api.multi
    def action_send_mail(self):
        pass

    @api.multi
    def action_print_service_order(self):
        return self.env.ref('service.action_report_service_order').report_action(self)

    @api.multi
    def action_print_pass_keluar(self):
        return self.env.ref('service.report_gate_pass').report_action(self)

    def action_service_invoice_create(self):
        for service in self:
            if service.work_stage not in ['done', 'delivered']:
                raise UserError(_('Stage must "Done" at least'))
            service.action_invoice_create()
            service.write({'state': 'ready'})
#             if service.invoice_method == 'b4repair':
#                 service.action_service_ready()
#             elif service.invoice_method == 'after_repair':
#                 service.write({'state': 'done'})
        return True

    def action_service_ready(self):
        if self.operations.filtered(lambda op: op.requested and not op.received):
            raise UserError(_('There are requested items not yet received'))
        if self.consumable_lines.filtered(lambda op:op.requested and not op.received):
            raise UserError(_('There are requested consumables not yet received'))
        self.mapped('operations').write({'state': 'confirmed'})
        return self.write({'state': '2binvoiced', 'work_stage': 'done'})

    @api.multi
    def action_service_end(self):
        if self.filtered(lambda service: service.state != 'ready'):
            raise UserError(_("Service must done in order to close."))
        if self.filtered(lambda service: not service.items_ok):
            raise UserError(_('All items must received and purchased'))
        if self.filtered(lambda service: service.work_stage != 'delivered'):
            raise UserError(_('Stage must "Delivered" to end Service.'))
        if self.filtered(lambda service: service.bill_type == 'claim' and not service.own_risk_invoiced):
            raise UserError(_('Own Risk not yet billed'))
        for service in self:
            service.write({'repaired': True})
            vals = {'state': 'done'}
            if not service.invoiced and service.invoice_method == 'after_repair':
                vals['state'] = '2binvoiced'
            service.write(vals)
        return True

    @api.multi
    def action_invoice_or_create(self):
        InvoiceLine = self.env['account.invoice.line']
        Invoice = self.env['account.invoice']
        own_risk_found = False
        for service in self.filtered(lambda x: not x.own_risk_invoiced):
#             own_risk = service.others_lines.search([('product_id.name', '=', 'Own Risk')], limit=1)
            if service.bill_type != 'claim':
                raise UserError(_('Only Insurance Claim needs Own Risk billing'))
            if service.own_risk_invoiced:
                raise UserError(_('Own Risk had invoiced'))
            if not service.others_lines:
                raise UserError(_('No "Others" section'))

            for other in service.others_lines:
                if other.name == 'Own Risk':
                    own_risk_found = True
                    if other.product_id.property_account_income_id:
                        account_id = other.product_id.property_account_income_id.id
                    elif other.product_id.categ_id.property_account_income_categ_id:
                        account_id = other.product_id.categ_id.property_account_income_categ_id.id
                    else:
                        raise UserError(_('No account defined for product "%s%".') % other.product_id.name)

                    invoice_or = Invoice.create({
                        # 'name': service.name,
                        'origin': '%s-%s' % ('OR', service.name),
                        'origin_type': 'own_risk',
                        'service_id': service.id,
                        'eq_name': service.equipment_id.name,
                        'type': 'out_invoice',
                        'account_id': service.partner_id.property_account_receivable_id.id,
                        # 'partner_id': service.partner_invoice_id.id or service.partner_id.id,
                        'partner_id': service.partner_id.id,
                        'currency_id': service.currency_id.id,
                        # 'comment': service.quotation_notes,
                        'fiscal_position_id': service.partner_id.property_account_position_id
                    })

                    if invoice_or:
                        InvoiceLine.create({
                            'invoice_id': invoice_or.id,
                            'name': other.name,
                            'origin': other.name,
                            'account_id': account_id,
                            'quantity': other.product_uom_qty,
                            'invoice_line_tax_ids': [(6, 0, [x.id for x in other.tax_id])],
                            'uom_id': other.product_uom.id,
                            'product_id': other.product_id and other.product_id.id or False,
                            'product_category': other.product_id.categ_id.name,
                            'price_unit': other.price_unit,
                            'price_subtotal': other.product_uom_qty * other.price_unit
                        })
                    service.write({'own_risk_invoiced': True, 'invoice_or_id': invoice_or.id})

            if not own_risk_found:
                raise UserError(_('No Own Risk line found in "Others" section'))

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
            inv_partner = service.partner_invoice_id
            if not service.partner_id.id and not service.partner_invoice_id.id:
                raise UserError(_('You have to select an invoice address in the service form.'))
            if not service.partner_invoice_id.id:
                inv_partner = service.partner_id
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
                    # if not service.partner_invoice_id.property_account_receivable_id:
                    if not inv_partner.property_account_receivable_id:
                        raise UserError(_('No account defined for partner "%s"' % service.partner_invoice_id.name))
                    invoice = Invoice.create({
                        # 'name': service.name,
                        'origin': service.name,
                        'origin_type': 'service',
                        'service_id': service.id,
                        'eq_name': service.equipment_id.name,
                        'type': 'out_invoice',
                        'account_id': service.partner_invoice_id.property_account_receivable_id.id,
                        # 'partner_id': service.partner_invoice_id.id or service.partner_id.id,
                        'partner_id': inv_partner.id,
                        'currency_id': service.currency_id.id,
                        # 'comment': service.quotation_notes,
                        'fiscal_position_id': service.partner_invoice_id.property_account_position_id
                    })
                    
                    invoices_group[service.partner_invoice_id.id] = invoice

                service.write({'invoiced': True, 'invoice_id': invoice.id})

                if service.operations:
                    for operation in service.operations:
                        if not operation.approved:
                            continue

                        if group:
                            name = service.name + '-' + operation.name
                        else:
                            name = operation.name

                        if operation.product_id.property_account_income_id:
                            account_id = operation.product_id.property_account_income_id.id
                        elif operation.product_id.categ_id.property_account_income_categ_id:
                            account_id = operation.product_id.categ_id.property_account_income_categ_id.id
                        else:
                            raise UserError(_('No account defined for product "%s".') % operation.product_id.name)

                        invoice_line = InvoiceLine.create({
                            'invoice_id': invoice.id,
                            'name': name,
                            'origin': service.name,
                            'account_id': account_id,
                            'quantity': operation.product_uom_qty,
                            'invoice_line_tax_ids': [(6, 0, [x.id for x in operation.tax_id])],
                            'uom_id': operation.product_uom.id,
                            'product_id': operation.product_id and operation.product_id.id or False,
                            'product_category': operation.product_id.categ_id.name,
                            'price_unit': operation.price_unit,
                            'price_subtotal': operation.product_uom_qty * operation.price_unit
                        })
                        operation.write({'invoiced': True, 'invoice_line_id': invoice_line.id})

                if service.fees_lines:
                    for fee in service.fees_lines:
                        if not fee.approved:
                            continue

                        if group:
                            name = service.name + '-' + fee.name
                        else:
                            name = fee.name
                        if not fee.product_id:
                            raise UserError(_('No product defined on fees.'))
                        if fee.product_id.property_account_income_id:
                            account_id = fee.product_id.property_account_income_id.id
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
                            'product_category': fee.product_id.categ_id.name,
                            'price_unit': fee.price_unit,
                            'price_subtotal': fee.product_uom_qty * fee.price_unit
                        })
                        fee.write({'invoiced': True, 'invoice_line_id': invoice_line.id})

                if service.others_lines:
                    for other in service.others_lines:
#                         if not other.approved:
#                             continue

                        if group:
                            name = service.name + '-' + other.name
                        else:
                            name = other.name
                        if not other.product_id:
                            raise UserError(_('No product defined on others.'))

                        if other.product_id.property_account_income_id:
                            account_id = other.product_id.property_account_income_id.id
                        elif other.product_id.categ_id.property_account_income_categ_id:
                            account_id = other.product_id.categ_id.property_account_income_categ_id.id
                        else:
                            raise UserError(_('No account defined for product "%s".') % other.product_id.name)
                        
                        price = other.price_unit
                        if other.deductible:
                            price = other.price_unit * (-1)
                        
                        if other.name == 'Own Risk':
#                             price = other.price_unit * (-1)
                            if service.bill_type == 'claim':
                                invoice.write({'own_risk': other.price_subtotal})
                        
                        invoice_line = InvoiceLine.create({
                            'invoice_id': invoice.id,
                            'name': name,
                            'origin': other.name,
                            'account_id': account_id,
                            'quantity': other.product_uom_qty,
                            'invoice_line_tax_ids': [(6, 0, [x.id for x in other.tax_id])],
                            'uom_id': other.product_uom.id,
                            'product_id': other.product_id and other.product_id.id or False,
                            'product_category': other.product_id.categ_id.name,
                            'price_unit': price,  # other.price_unit,
                            'price_subtotal': other.product_uom_qty * price,  # other.price_unit
                            'deductible': other.deductible
                        })

                invoice.compute_taxes()
                # invoice_or.compute_taxes()
                # invoice.create_wht_tax()
                res[service.id] = invoice.id
        return res

    @api.multi
    def action_created_invoice(self):
        self.ensure_one()
        return {
            'name': _('Invoice created'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'view_id': self.env.ref('account.invoice_form').id,
            'target': 'current',
            'res_id': self.invoice_id.id,
        }

    @api.multi
    def action_created_invoice_or(self):
        self.ensure_one()
        return {
            'name': _('Invoice OR created'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'view_id': self.env.ref('account.invoice_form').id,
            'target': 'current',
            'res_id': self.invoice_or_id.id,
        }

    @api.multi
    def action_service_cancel_draft(self):
        return self.write({'state': 'draft'})

    @api.multi
    def action_export_xls(self):
        file_name = '/home/kmsadmin/temp/service_order.xlsx'
        workbook = xlsxwriter.Workbook(file_name, {'in_memory': True})
        worksheet = workbook.add_worksheet('SPK')

        number_format = workbook.add_format({
            'num_format': '#,##0',
            'border': 1
        })
        border_format = workbook.add_format({
            'border': 1
        })
        header_format_main = workbook.add_format({
            'font_size': 14,
            'bold': True,
            'align': 'center',
            'valign': 'center',
            'border': 1
        })
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'center',
            'border': 1
        })
        header_format_wrap = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'center',
            'text_wrap': True,
            'border': 1
        })
        section_format = workbook.add_format({
            'border': 1,
            'bold': True
        })
        center_format = workbook.add_format({
            'align': 'center',
            'valign': 'center',
            'border': 1
        })
        merged_format_top = workbook.add_format({
            'align': 'left',
            'valign': 'top',
            'border': 1
        })
        merged_format_bottom = workbook.add_format({
            'align': 'center',
            'valign': 'bottom',
            'border': 1
        })
        wrap_format = workbook.add_format({
            'text_wrap': True,
            'border': 1
        })
        wrap_format_top = workbook.add_format({
            'text_wrap': True,
            'valign': 'top',
            'border': 1
        })

        # worksheet.merge_range('A1:G1', 'ESTIMASI BIAYA PERBAIKAN KENDARAAN', header_format_main)
        worksheet.merge_range(1, 0, 1, 1, 'No. Estimasi', border_format)
        worksheet.write(1, 2, self.name, border_format)
        worksheet.merge_range(2, 0, 2, 1, 'Asuransi', border_format)
        worksheet.write(2, 2, self.insurance_id.name or '', border_format)
        worksheet.merge_range(3, 0, 3, 1, 'Merek Mobil', border_format)
        worksheet.write(3, 2, '%s %s' % (self.make, self.model), border_format)
        worksheet.merge_range(4, 0, 4, 1, 'No. Polisi / Chassis', wrap_format)
        worksheet.write(4, 2, '%s / %s' % (self.equipment_id.name, self.chassis_no), wrap_format)
        worksheet.merge_range(5, 0, 5, 1, 'Warna', border_format)
        worksheet.write(5, 2, self.base_colour or '', border_format)

        worksheet.merge_range(1, 3, 1, 4, 'Nama Pelanggan', border_format)
        worksheet.merge_range(1, 5, 1, 6, self.partner_id.name, wrap_format)
        worksheet.merge_range(2, 3, 2, 4, 'Alamat', border_format)
        worksheet.merge_range(2, 5, 2, 6, self.partner_id.street or '', border_format)
        worksheet.merge_range(3, 3, 3, 4, 'Telepon', border_format)
        worksheet.merge_range(3, 5, 3, 6, self.partner_id.phone or '', border_format)
        worksheet.merge_range(4, 3, 4, 4, 'No. Polis Asuransi', wrap_format)
        worksheet.merge_range(4, 5, 4, 6, self.policy_no or '', wrap_format)
        worksheet.merge_range(5, 3, 5, 4, 'No. Berkas', border_format)
        worksheet.merge_range(5, 5, 5, 6, self.claim_id or '', border_format)
        # details
        worksheet.write(7, 0, 'No.', header_format)
        worksheet.merge_range(7, 1, 7, 3, 'KETERANGAN', header_format)
        worksheet.write(7, 4, 'QTY', header_format)
        worksheet.write(7, 5, 'HARGA SATUAN \n(Rp.)', header_format_wrap)
        worksheet.write(7, 6, 'TOTAL HARGA \n(Rp.)', header_format_wrap)

        worksheet.merge_range(8, 0, 8, 6, 'PERBAIKAN DAN PENGECATAN', section_format)
        row = 9
        idx = 1
        total_jasa = 0
        for o in self.fees_lines:
            worksheet.write(row, 0, idx, border_format)
            worksheet.write(row, 1, '', border_format)
            worksheet.merge_range(row, 2, row, 3, o.name, border_format)
            worksheet.write(row, 4, o.product_uom_qty, border_format)
            worksheet.write(row, 5, o.price_unit, number_format)
            worksheet.write(row, 6, o.price_subtotal, number_format)
            total_jasa += o.price_subtotal
            row += 1
            idx += 1
        worksheet.merge_range(row, 0, row, 5, 'Total Jasa', section_format)
        worksheet.write(row, 6, total_jasa, number_format)
        row += 1

        worksheet.merge_range(row, 0, row, 6, 'PENGGANTIAN SPAREPART', section_format)
        row += 1
        idx = 1
        total_spareparts = 0
        for r in self.operations:
            worksheet.write(row, 0, idx, border_format)
            worksheet.write(row, 1, r.part_number, border_format)
            worksheet.merge_range(row, 2, row, 3, r.name, border_format)
            worksheet.write(row, 4, r.product_uom_qty, border_format)
            worksheet.write(row, 5, r.price_unit, number_format)
            worksheet.write(row, 6, r.price_subtotal, number_format)
            total_spareparts += r.price_subtotal
            row += 1
            idx += 1
        worksheet.merge_range(row, 0, row, 5, 'Total Sparepart', section_format)
        worksheet.write(row, 6, total_spareparts, number_format)

        row += 1
        worksheet.merge_range(row, 0, row, 5, 'Total', section_format)
        worksheet.write(row, 6, self.amount_untaxed, number_format)

        row += 1
        total = total_spareparts + total_jasa
        worksheet.merge_range(row, 0, row, 1, 'Terbilang:', border_format)
        worksheet.merge_range(row, 2, row, 4, num2words(total, lang='id'), wrap_format)
        worksheet.merge_range(row, 5, row, 6, '%s, %s' % ('Bekasi', fields.Date.today()), center_format)

        row += 1
        worksheet.merge_range(row, 0, row + 2, 1, 'Catatan', merged_format_top)
        worksheet.merge_range(row, 2, row + 2, 4, self.quotation_notes or '', wrap_format_top)
        worksheet.merge_range(row, 5, row + 2, 6, self.service_advisor or '', merged_format_bottom)
        # Save workbook
        workbook.close()
        # read and save as binary
        with open(file_name, "rb") as file:
            file_base64 = base64.b64encode(file.read())

        record_id = self.env['service.order.excel.wizard'].create(
            {'excel_file': file_base64, 'excel_file_name': 'testing.xls'})

        return {
            'name': _('Excel file created'),
            'view_mode': 'form',
            'res_id': record_id.id,
            'res_model': 'service.order.excel.wizard',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            # 'context': context
            'target': 'new',
        }

class ServiceOrderExcelWizard(models.TransientModel):
    _name = 'service.order.excel.wizard'

    excel_file = fields.Binary('Excel File')
    excel_file_name = fields.Char('Excel File Name')

class ServiceLine(models.Model):
    _name = 'service.line'
    _description = 'Service Line (Part)'

    name = fields.Text('Description')
    # part_number = fields.Char('Part Number')
    service_id = fields.Many2one(
        'service.order', 'Service Order reference',
        index=True, ondelete='cascade')
    supply_type = fields.Selection(
        SUPPLY_TYPES, 'Supply Type', index=True, required=True,
        default='vendor')
    product_id = fields.Many2one('product.product', 'Part Number') # , required=True)
    part_number = fields.Char('Kode Part Admin')
    product_uom_qty = fields.Float('Quantity', default=1.0, required=True)
    product_uom = fields.Many2one(
        'uom.uom', 'Product Unit od Measure')
    estimate_unit = fields.Float('Estimation', digits=(12,0))
    price_unit = fields.Float('Unit Price', digits=(12,0))
    tax_id = fields.Many2many(
        'account.tax', 'service_operation_line_tax', 'service_operation_line_id', 'tax_id', 'Taxes')
    price_subtotal = fields.Float('Subtotal', compute="_compute_price_subtotal", store=True, digits=(12,0))
    invoiced = fields.Boolean('Invoiced', copy=False, readonly=True)
    rejected = fields.Boolean('Repaired', copy=False, readonly=True)
    invoice_line_id = fields.Many2one(
        'account.invoice.line', 'Invoice Line', copy=False)

    # Production line ---- #
    location_id = fields.Many2one(
        'stock.location', 'Source Location', index=True)
    location_dest_id = fields.Many2one(
        'stock.location', 'Dest. Location', index=True)
    requested = fields.Boolean('Requested', copy=False)
    received = fields.Boolean('Received', copy=False)
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
    approved = fields.Boolean('Approved', default=False)
    cost_unit = fields.Float('Unit Cost', digits=(12,0)) #, required=True)
    # cost_tax_id = fields.Many2many(
    #     'account.tax', 'service_fee_line_tax', 'service_fee_line_id', 'tax_id', 'Taxes')
    cost_subtotal = fields.Float('Subtotal', compute='_compute_cost_subtotal', store=True, digits=(12,0))
    # purchased = fields.Boolean('Purchased', copy=False, required=True)
    # purchase_line_id = fields.Many2one(
    #     'purchase.order.line', 'Purchase Line', copy=False)
    # vendor_id = fields.Many2one('res.partner', 'Vendor', copy=False)
    is_robbing = fields.Boolean('Robbing?', copy=False)
    eq_robbed = fields.Char('Nopol Robbed')
    is_robbing_done = fields.Boolean('Robbing Done?', copy=False)

    @api.one
    @api.depends('price_unit', 'service_id', 'product_uom_qty', 'product_id', 'tax_id') #, 'service_id.invoice_method')
    def _compute_price_subtotal(self):
        taxes = self.tax_id.compute_all(self.price_unit, self.service_id.currency_id, self.product_uom_qty, self.product_id, self.service_id.partner_id)
        self.price_subtotal = taxes['total_excluded']

    @api.onchange('supply_type', 'service_id')
    def onchange_operation_type(self):
        """ On change of operation type it sets source location, destination location
        and to invoice field.
        @param product: Changed operation type.
        @param guarantee_limit: Guarantee limit of current record.
        @return: Dictionary of values.
    _name = 'service.order'
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

    @api.one
    @api.depends('cost_unit', 'service_id', 'product_uom_qty', 'product_id')
    def _compute_cost_subtotal(self):
        self.cost_subtotal = self.product_uom_qty * self.cost_unit

    @api.onchange('price_unit')
    def onchange_price_unit(self):
        if not self.estimate_unit:
#         if not self.service_id.has_confirmed:
            self.estimate_unit = self.price_unit

    @api.onchange('product_uom')
    def _onchange_product_uom(self):
        if self.supply_type == 'self':
            self.price_unit = self.product_id.list_price
            self.estimate_unit = self.product_id.list_price
            self.cost_unit = self.product_id.standard_price

    @api.onchange('service_id', 'product_id', 'product_uom_qty')
    def onchange_product_id(self):
        """ On change of product it sets product quantity, tax, name, uom, price
        and price subtotal. """
        partner = self.service_id.partner_invoice_id
        # self.lot_id = False

        # if not self.product_id or not self.product_uom_qty:
        # return
        if self.product_id:
            self.name = self.product_id.name
            self.product_uom = self.product_id.uom_id.id
        if partner and self.product_id:
            self.tax_id = partner.property_account_position_id.map_tax(self.product_id.taxes_id, self.product_id, partner).ids

class ServiceFee(models.Model):
    _name = 'service.fee'
    _description = 'Service Fees'

    name = fields.Text('Description', index=True)
    service_id = fields.Many2one(
        'service.order', 'Service Order Reference',
        index=True, ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', 'Service Fee', required=True)
    product_uom_qty = fields.Float('Quantity', required=True, default=1.0)
    estimate_unit = fields.Float('Estimation', digits=(12,0))
    price_unit = fields.Float('Unit Price', required=True, digits=(12,0))
    product_uom = fields.Many2one('uom.uom', 'Product Unit of Measure', required=True)
    price_subtotal = fields.Float('Subtotal', compute='_compute_price_subtotal', store=True, digits=(12,0))
    tax_id = fields.Many2many('account.tax', 'service_fee_line_tax', 'service_fee_line_id', 'tax_id', 'Taxes')
    invoice_line_id = fields.Many2one('account.invoice.line', 'Invoice Line', copy=False, readonly=True)
    approved = fields.Boolean('Approved', default=False)
    invoiced = fields.Boolean('Invoiced', copy=False, readonly=False)

    # ------ Production ------ #
    cost_unit = fields.Float('Unit Cost', required=True, digits=(12,0))
    # cost_tax_id = fields.Many2many(
    #     'account.tax', 'service_fee_line_tax', 'service_fee_line_id', 'tax_id', 'Taxes')
    cost_subtotal = fields.Float('Subtotal', compute='_compute_cost_subtotal', store=True, digits=(12,0))
    purchased = fields.Boolean('Purchased', copy=False, required=True)
    purchase_line_id = fields.Many2one(
        'purchase.order.line', 'Purchase Line', copy=False)
    vendor_ids = fields.Many2many('res.partner', 'service_fee_vendor', 'service_fee_id', 'vendor_id', 'Vendors')

    @api.one
    @api.depends('price_unit', 'service_id', 'product_uom_qty', 'product_id')
    def _compute_price_subtotal(self):
        taxes = self.tax_id.compute_all(self.price_unit, self.service_id.currency_id, self.product_uom_qty, self.product_id, self.service_id.partner_id)
        self.price_subtotal = taxes['total_excluded']

    @api.one
    @api.depends('cost_unit', 'service_id', 'product_uom_qty', 'product_id')
    def _compute_cost_subtotal(self):
        self.cost_subtotal = self.product_uom_qty * self.cost_unit

    @api.onchange('price_unit')
    def onchange_price_unit(self):
        if not self.estimate_unit:
#         if not self.service_id.has_confirmed:
            self.estimate_unit = self.price_unit

    @api.onchange('product_uom')
    def _onchange_product_uom(self):
        self.price_unit = self.product_id.list_price
        self.estimate_unit = self.product_id.list_price
        self.cost_unit = self.product_id.standard_price

    @api.onchange('service_id', 'product_id', 'product_uom_qty')
    def onchange_product_id(self):
        if not self.product_id:
            return

        partner = self.service_id.partner_invoice_id
        if self.product_id:
            self.name = self.product_id.name
            self.product_uom = self.product_id.uom_id.id

#         if self.service_id.vendor_ids:
#             self.vendor_ids = self.service_id.vendor_ids

        if partner and self.product_id:
            self.tax_id = partner.property_account_position_id.map_tax(self.product_id.taxes_id, self.product_id, partner).ids

class ServiceOther(models.Model):
    _name = 'service.other'
    _description = 'Service Others'

    name = fields.Text('Description')
    # other_code = fields.Char('Item Code')
    service_id = fields.Many2one(
        'service.order', 'Service Order Reference',
        index=True, ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', 'Service Other', required=True)
    product_uom_qty = fields.Float('Quantity', required=True, default=1.0)
    estimate_unit = fields.Float('Estimation')
    price_unit = fields.Float('Unit Price', required=True)
    product_uom = fields.Many2one('uom.uom', 'Product Unit of Measure', required=True)
    price_subtotal = fields.Float('Subtotal', compute='_compute_price_subtotal', store=True, digits=0)
    tax_id = fields.Many2many('account.tax', 'service_others_line_tax', 'service_others_line_id', 'tax_id', 'Taxes')
    approved = fields.Boolean('Approved', default=True)
    invoice_line_id = fields.Many2one('account.invoice.line', 'Invoice Line', copy=False, readonly=True)
    invoiced = fields.Boolean('Invoiced', copy=False, readonly=True)
    deductible = fields.Boolean('Deductible')

    # ------ Production ------ #
    cost_unit = fields.Float('Unit Cost', required=True)
    cost_tax_id = fields.Many2many(
        'account.tax', 'service_others_cost_tax', 'service_others_line_id', 'cost_tax_id', 'Taxes')
    cost_subtotal = fields.Float('Cost Subtotal', compute='_compute_cost_subtotal', store=True, digits=0)
    purchased = fields.Boolean('Purchased', copy=False, required=True)
    purchase_line_id = fields.Many2one(
        'purchase.order.line', 'Purchase Line', copy=False)
    # vendor_id = fields.Many2one('res.partner', 'Vendor', copy=False)
    vendor_ids = fields.Many2many('res.partner', 'service_other_vendor', 'service_other_id', 'vendor_id', 'Vendors')

    @api.one
    @api.depends('price_unit', 'service_id', 'product_uom_qty', 'product_id')
    def _compute_price_subtotal(self):
        taxes = self.tax_id.compute_all(self.price_unit, self.service_id.currency_id, self.product_uom_qty, self.product_id, self.service_id.partner_id)
        self.price_subtotal = taxes['total_excluded']

    @api.one
    @api.depends('cost_unit', 'service_id', 'product_uom_qty', 'product_id')
    def _compute_cost_subtotal(self):
        self.cost_subtotal = self.product_uom_qty * self.cost_unit

    @api.onchange('product_uom')
    def _onchange_product_uom(self):
        if self.name == 'Own Risk':
            self.deductible = True
        self.price_unit = self.product_id.list_price
        self.estimate_unit = self.product_id.list_price
        self.cost_unit = self.product_id.standard_price

    @api.onchange('service_id', 'product_id', 'product_uom_qty')
    def onchange_product_id(self):
        if not self.product_id:
            return

        partner = self.service_id.partner_invoice_id
        if self.product_id:
            self.name = self.product_id.name
            self.product_uom = self.product_id.uom_id.id

        if partner and self.product_id:
            self.tax_id = partner.property_account_position_id.map_tax(self.product_id.taxes_id, self.product_id, partner).ids

class ServiceConsumable(models.Model):
    _name = 'service.consumable'
    _description = 'Consumable lines'

    name = fields.Text('Description')
    service_id = fields.Many2one(
        'service.order', 'Service Order Reference',
        index=True, ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', 'Bahan Baku', required=True)
    product_uom_qty = fields.Float('Quantity', required=True, default=1.0)
    product_uom = fields.Many2one('uom.uom', 'Product Unit of Measure', required=True)
    cost_unit = fields.Float('Unit Cost', required=True, default=0.0)
    cost_tax_id = fields.Many2many(
        'account.tax', 'service_consumable_line_tax', 'service_consumable_line_id', 'cost_tax_id', 'Taxes')
    cost_subtotal = fields.Float('Subtotal', compute='_compute_cost_subtotal', store=True, digits=0)

    # Production line ---- #
    location_id = fields.Many2one(
        'stock.location', 'Source Location', index=True)
    location_dest_id = fields.Many2one(
        'stock.location', 'Dest. Location', index=True)
    requested = fields.Boolean('Requested', copy=False)
    received = fields.Boolean('Received', copy=False)
    move_id = fields.Many2one(
        'stock.move', 'Inventory Move', copy=False, readonly=True)
    lot_id = fields.Many2one('stock.production.lot', 'Lot/Serial')

    @api.one
    @api.depends('cost_unit', 'service_id', 'product_uom_qty', 'product_id')
    def _compute_cost_subtotal(self):
        self.cost_subtotal = self.product_uom_qty * self.cost_unit

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

    @api.onchange('product_uom')
    def _onchange_product_uom(self):
        self.cost_unit = self.product_id.standard_price

    @api.onchange('service_id')
    def onchange_service_id(self):
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
