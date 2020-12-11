##############################################################################
#
#    Copyright (C) 2015 Comunitea Servicios Tecnológicos All Rights Reserved
#    $Omar Castiñeira Saavedra <omar@comunitea.com>$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import models, fields, api, exceptions, _
from datetime import datetime
from odoo.exceptions import except_orm


class CrmClaimRma(models.Model):
    _inherit = 'crm.claim'
    _order = 'id desc'

    @api.multi
    def _has_category(self, expected_category):
        has_category = False
        for category in self.category_id:
            if category.parent_id.id == expected_category.id:
                has_category = True
        self.bool_category_id = has_category

    @api.multi
    def _check_category_id(self):
        expected_category = self.env['res.partner.category'].search([('name', '=', 'Certificado')])
        for claim in self:
            claim._has_category(expected_category)

    name = fields.Selection([('return', 'Return'),
                             ('rma', 'RMA')], 'Claim Subject',
                            required=True, default='rma')
    priority = fields.Selection(default='1', required=True, selection=[('1', 'No priority'),
                                                                       ('2', 'High'),
                                                                       ('3', 'Critical')])
    comercial = fields.Many2one("res.users", string="Comercial")
    country = fields.Many2one("res.country", string="Country")
    date = fields.Date('Claim Date', index=False,
                       default=fields.Date.context_today)
    write_date = fields.Datetime("Update date", readonly=True)
    date_received = fields.Date('Received Date')
    category_id = fields.Many2many(related='partner_id.category_id', readonly=True)
    bool_category_id = fields.Boolean(string="Category", compute=_check_category_id)
    aditional_notes = fields.Text("Aditional Notes")
    claim_inv_line_ids = fields.One2many("claim.invoice.line", "claim_id")
    allow_confirm_blocked = fields.Boolean('Allow confirm', copy=False)
    transport_incidence = fields.Boolean('Transport incidence')
    t_incidence_picking = fields.Char('Trp. inc. picking')
    warehouse_location = fields.Selection([('madrid1', 'Madrid - Avd. del Sol'),
                                           ('madrid2', 'Madrid - Casablanca'),
                                           ('italia', 'Italia - Arcore'),
                                           ('transit', 'In transit')], "Warehouse Location")

    check_states = ['substate_received', 'substate_process', 'substate_due_receive']

    @api.multi
    def write(self, vals):
        if 'stage_id' in vals:
            stage_ids = []
            stage_repaired_id = self.env.ref('crm_claim.stage_claim2').id
            stage_ids.append(stage_repaired_id)
            stage_pending_shipping_id = self.env.ref('crm_claim_rma_custom.stage_claim6').id
            stage_ids.append(stage_pending_shipping_id)

            stage_received_id = self.env['crm.claim.stage'].search([('name', '=', 'Recibido')]).id
            if vals['stage_id'] == stage_received_id and \
                    not (self.warehouse_location or vals.get('warehouse_location', False)):
                raise exceptions.UserError(_('Please, select the warehouse location of the RMA'))

            if vals['stage_id'] in stage_ids:
                for line in self.claim_line_ids:
                    line_state = self.env['ir.model.data'].search([('model', '=', 'substate.substate'),
                                                                   ('module', '=', 'crm_claim_rma_custom'),
                                                                   ('res_id', '=', line.substate_id.id)])
                    if vals['stage_id'] == stage_repaired_id:
                        if line_state.name in self.check_states:
                            raise except_orm(_('Warning!'),
                                             _("One or more products aren't review yet!"))
                    else:
                        if line_state.name != 'substate_pending_shipping':
                            raise except_orm(_('Warning!'),
                                             _("One or more products aren't pending shipping yet!"))

        return super(CrmClaimRma, self).write(vals)

    @api.model
    def create(self, vals):
        if vals.get('name', False):
            vals['name'] = vals['name'].split(' ')[0]
        return super(CrmClaimRma, self).create(vals)

    @api.model
    def _get_sequence_number(self):
        seq_obj = self.env['ir.sequence']
        supplier_type = self.env.ref('crm_claim_type.crm_claim_type_supplier').id
        if 'claim_type' in self.env.context and self.env.context['claim_type'] == supplier_type:
            res = seq_obj.get('crm.claim.rma.supplier') or '/'
        else:
            res = seq_obj.get('crm.claim.rma') or '/'
        return res

    @api.multi
    def calculate_invoices(self):
        """
        Calculate invoices using data "Product Return of SAT"
        """
        for claim_obj in self:
            claim_inv_line_obj = self.env['claim.invoice.line']
            for invoice_line in claim_obj.claim_inv_line_ids:
                if not invoice_line.invoiced:
                    invoice_line.unlink()
            for claim_line in claim_obj.claim_line_ids:
                vals = {}
                taxes_ids = []
                if claim_line.invoice_id:
                    claim_inv_lines = claim_inv_line_obj.search([('claim_line_id', '=', claim_line.id)])
                    if claim_inv_lines:
                        continue
                    for inv_line in claim_line.invoice_id.invoice_line_ids:
                        if inv_line.product_id == claim_line.product_id:
                            if inv_line.invoice_line_tax_ids:
                                taxes_ids = \
                                    [x.id for x in inv_line.invoice_line_tax_ids]
                            vals = {
                                'invoice_id': inv_line.invoice_id.id,
                                'claim_id': claim_line.claim_id.id,
                                'claim_number': claim_line.claim_id.number,
                                'claim_line_id': claim_line.id,
                                'product_id': inv_line.product_id.id,
                                'product_description': inv_line.product_id.name,
                                'discount': inv_line.discount,
                                'qty': claim_line.product_returned_quantity,
                                'price_unit': inv_line.price_unit,
                                'cost_unit': inv_line.product_id.standard_price,
                                'tax_ids': [(6, 0, taxes_ids)]
                            }
                            break
                    if not vals:
                        raise exceptions.Warning(
                            _("There is at least one line of the claim with \
                               an incorrect invoice"))
                if vals:
                    claim_inv_line_obj.create(vals)

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        result = super().onchange_partner_id()
        if self.partner_id:
            self.delivery_address_id = self.partner_id
            self.team_id = self.partner_id.team_id   # Get team_id from res.partner
            self.country = self.partner_id.country_id    # Get country_id from res.partner
            if self.partner_id.user_id:
                self.comercial = self.partner_id.user_id.id
            if self.partner_id.rma_warn_msg:
                self.description = self.partner_id.rma_warn_msg
        return result

    @api.onchange('name')
    def onchange_name(self):
        if self.name == 'return':
            self.invoice_type = 'refund'
        elif self.name == 'rma':
            self.invoice_type = 'invoice'

    @api.multi
    def make_refund_invoice(self):
        for claim_obj in self:
            invoice = False
            invoice_name = set()
            for line in claim_obj.claim_inv_line_ids:
                if not line.invoiced:
                    if line.invoice_id.name:
                        invoice_name.add(line.invoice_id.name)
                    invoice = True

            if not invoice:
                raise exceptions.Warning(_("Any line to invoice"))

            description = ' '.join(invoice_name)

            # TODO-> Revisar: antes sale_refund
            domain_journal = [('type', '=', 'sale')]
            acc_journal_obj = self.env['account.journal']
            acc_journal_ids = acc_journal_obj.search(domain_journal)
            header_vals = {
                'partner_id': claim_obj.partner_id.id,
                'fiscal_position_id':
                    claim_obj.partner_id.property_account_position_id.id,
                'date_invoice': datetime.now().strftime('%Y-%m-%d'),
                'journal_id': acc_journal_ids[0].id,
                'account_id':
                    claim_obj.partner_id.property_account_receivable_id.id,
                'currency_id':
                    claim_obj.partner_id.property_product_pricelist.currency_id.id,
                'company_id': claim_obj.company_id.id,
                'user_id': self.env.user.id,
                'team_id': claim_obj.partner_id.team_id.id,
                'claim_id': claim_obj.id,
                'type': 'out_refund',
                'payment_term_id': False,  # Pago inmediato en rectificativas claim_obj.partner_id.property_payment_term_id.id,
                'payment_mode_id':
                    claim_obj.partner_id.customer_payment_mode_id.id,
                'mandate_id': claim_obj.partner_id.valid_mandate_id.id,
                'name': description
            }
            inv_obj = self.env['account.invoice']
            invoice_id = inv_obj.create(header_vals)
            fp_obj = self.env['account.fiscal.position']
            for line in claim_obj.claim_inv_line_ids:
                if line.invoiced:
                    continue
                if line.product_id:
                    account_id = line.product_id.property_account_income_id.id
                    if not account_id:
                        account_id = \
                            line.product_id.categ_id. \
                            property_account_income_categ_id.id
                    else:
                        account_id = line.product_id. \
                            property_account_expense_id.id
                        if not account_id:
                            account_id = \
                                line.product_id.categ_id. \
                                property_account_expense_categ_id.id
                else:
                    prop = self.env['ir.property'].get('property_account_income_categ_id', 'product.category')
                    account_id = prop and prop.id or False
                account_id = fp_obj.map_account(account_id)
                vals = {
                    'invoice_id': invoice_id.id,
                    'name': line.product_description,
                    'product_id': line.product_id.id,
                    'account_id': account_id,
                    'quantity': line.qty,
                    'claim_line_id': line.claim_line_id.id,
                    'price_unit': line.price_unit,
                    'cost_unit': line.cost_unit,
                    'uos_id': line.product_id.uom_id.id,
                    'discount': line.discount,
                    'account_analytic_id': False
                }
                if line.tax_ids:
                    taxes_ids = fp_obj.map_tax(line.tax_ids)
                    vals['invoice_line_tax_ids'] = [(6, 0, taxes_ids.ids)]
                line_obj = self.env['account.invoice.line']
                line_obj.create(vals)

                line.invoiced = True

            invoice_id.compute_taxes()
            invoice_id.action_invoice_open()

            data_pool = self.env['ir.model.data']
            action_id = data_pool.xmlid_to_res_id('crm_claim_rma.act_crm_claim_rma_refunds_out')
            if action_id:
                action = self.env.ref('crm_claim_rma.act_crm_claim_rma_refunds_out').read()[0]
                action['domain'] = "[('id','in', [" + str(invoice_id.id) + "])]"
                return action


class ClaimInvoiceLine(models.Model):
    _name = 'claim.invoice.line'
    _rec_name = 'product_description'
    _order = 'sequence,id'

    sequence = fields.Integer()
    claim_id = fields.Many2one('crm.claim', 'Claim')
    claim_number = fields.Char("Claim Number")
    claim_line_id = fields.Many2one('claim.line', 'Claim lne')
    product_id = fields.Many2one("product.product", "Product Code")
    product_description = fields.Char("Product Description", required=True)
    invoice_id = fields.Many2one("account.invoice", "Invoice")
    price_unit = fields.Float("Price Unit")
    cost_unit = fields.Float("Cost Unit")
    price_subtotal = fields.Float("Price Subtotal", compute="_get_subtotal",
                                  readonly=True)
    tax_ids = fields.Many2many("account.tax", "claim_line_tax",
                               "claimline_id", "tax_id", string="Taxes")
    discount = fields.Float("Discount")
    qty = fields.Float("Quantity", default="1")
    invoiced = fields.Boolean("Invoiced")

    @api.multi
    def _get_subtotal(self):
        for claim_line in self:
            claim_line.price_subtotal = claim_line.qty * claim_line.price_unit * ((100.0 - claim_line.discount) / 100.0)

    @api.onchange("product_id", "invoice_id")
    def onchange_product_id(self):
        if self.claim_id.partner_id:
            if self.product_id:
                taxes_ids = []
                if self.invoice_id:
                    # res['value'] = {'invoice_id': self.invoice_id.id}
                    any_line = False
                    for line in self.invoice_id.invoice_line_ids:
                        if not self.product_id == line.product_id:
                            any_line = False
                        else:
                            any_line = True
                            price = line.price_unit
                            taxes_ids = line.invoice_line_tax_ids
                            break
                    if not any_line:
                        raise exceptions.Warning(_('Selected product is not \
                                                    in the invoice'))
                else:
                    pricelist_obj = \
                        self.claim_id.partner_id.property_product_pricelist
                    price = pricelist_obj.price_get(self.product_id.id, 1.0)
                    if price:
                        price = price[pricelist_obj.id]
                self.product_description = self.product_id.name
                self.qty = 1.0
                self.price_unit = price
                self.price_subtotal = price
                self.discount = 0.0
                if taxes_ids:
                    self.tax_ids = taxes_ids
                else:
                    fpos = self.claim_id.partner_id.property_account_position_id
                    self.tax_ids = fpos.map_tax(self.product_id.product_tmpl_id.taxes_id)
            else:
                self.price_subtotal = self.discount and \
                                      self.qty * self.price_unit - (self.discount *
                                                                    self.price_unit / 100) or \
                                      self.qty * self.price_unit
        else:
            raise exceptions.Warning(_('Partner not selected'))

    @api.onchange("qty", "price_unit", "discount")
    def onchange_values(self):
        if self.product_id and self.invoice_id:
            for line in self.invoice_id.invoice_line_ids:
                if line.product_id == self.product_id and line.quantity < self.qty:
                    raise exceptions.Warning(_('Quantity cannot be bigger than the quantity specified on invoice'))
        price_subtotal = self.qty * self.price_unit * ((100.0 - self.discount) / 100.0)
        self.price_subtotal = price_subtotal

    @api.multi
    def unlink(self):
        for line in self:
            if line.invoiced:
                raise exceptions.Warning(_("Cannot delete an invoiced line"))
        return super(ClaimInvoiceLine, self).unlink()


class CrmClaimLine(models.Model):
    _inherit = 'claim.line'

    comercial = fields.Many2one("res.users", String="Comercial", related="claim_id.comercial")
    date_received = fields.Date(related="claim_id.date_received")
    name = fields.Char(required=False)
    invoice_id = fields.Many2one("account.invoice", string="Invoice")
    substate_id = fields. \
        Many2one(default=lambda self: self.env.ref('crm_claim_rma_custom.substate_due_receive').id)
    claim_name = fields.Selection(related='claim_id.name', readonly=True)

    res = {}

    @api.model
    def create(self, vals):
        if 'substate_id' not in vals.keys():
            vals['substate_id'] = self.env.ref(
                'crm_claim_rma_custom.substate_due_receive').id
        return super(CrmClaimLine, self).create(vals)

    @api.multi
    def write(self, vals):
        if 'repair_id' in vals.keys():
            vals['substate_id'] = self.env.ref(
                'crm_claim_rma_custom.substate_repaired').id
        if 'refund_line_id' in vals.keys():
            vals['substate_id'] = self.env.ref(
                'crm_claim_rma_custom.substate_refund').id
        if 'equivalent_product_id' in vals.keys():
            vals['substate_id'] = self.env.ref(
                'crm_claim_rma_custom.substate_replaced').id


        return super(CrmClaimLine, self).write(vals)

    @api.multi
    def action_split(self):
        for line in self:
            if line.product_returned_quantity > 1:
                for x in range(1, int(line.product_returned_quantity)):
                    line.copy(default={'product_returned_quantity': 1.0})
                line.product_returned_quantity = 1
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    @api.multi
    def create_repair(self):
        self.ensure_one()
        wzd = self.env['claim.make.repair'].create({'line_id': self.id})
        res = wzd.make()
        return res





