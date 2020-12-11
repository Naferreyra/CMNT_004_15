##############################################################################
#
#    Copyright 2013 Camptocamp
#    Copyright 2009-2013 Akretion,
#    Author: Emmanuel Samyn, Raphaël Valyi, Sébastien Beau,
#            Benoît Guillot, Joel Grand-Guillaume
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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

import calendar
import math
from odoo import fields, models, exceptions, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import (DEFAULT_SERVER_DATE_FORMAT,
                           DEFAULT_SERVER_DATETIME_FORMAT)
from odoo import SUPERUSER_ID, api

REPAIR_SELECTION = [
            ('draft', _('Quotation')),
            ('cancel', _('Cancelled')),
            ('confirmed', _('Confirmed')),
            ('under_repair', _('Under Repair')),
            ('ready', _('Ready to Repair')),
            ('2binvoiced', _('To be Invoiced')),
            ('invoice_except', _('Invoice Exception')),
            ('done', _('Repaired'))
            ]

MOVE_STATE_SELECTION = [('draft', _('New')), ('cancel', _('Cancelled')),
                        ('waiting', _('Waiting Another Move')),
                        ('confirmed', _('Waiting Availability')),
                        ('assigned', _('Available')), ('done', _('Done'))]


class SubstateSubstate(models.Model):
    """ To precise a state (state=refused; substates= reason 1, 2,...) """
    _name = "substate.substate"
    _description = "substate that precise a given state"

    active = fields.Boolean('Active', default=True)
    name = fields.Char('Sub state', required=True)
    substate_descr = fields.Text('Description', help="To give more information about the sub state")


class ClaimLine(models.Model):
    """
    Class to handle a product return line (corresponding to one invoice line)
    """
    _name = "claim.line"
    _description = "List of product to return"

    # Comment written in a claim.line to know about the warranty status
    WARRANT_COMMENT = {
        'valid': "Valid",
        'expired': "Expired",
        'not_define': "Not Defined"}

    # Method to calculate total amount of the line : qty*UP
    @api.multi
    def _line_total_amount(self):
        for line in self:
            line.return_value = (line.unit_sale_price *
                                 line.product_returned_quantity)

    @api.multi
    def copy_data(self, default=None):
        if default is None:
            default = {}
        std_default = {
            'move_in_id': False,
            'move_out_id': False,
            'refund_line_id': False,
        }
        std_default.update(default)
        return super(ClaimLine, self).copy_data(default=std_default)

    @api.model
    def get_warranty_return_partner(self):
        seller = self.env['product.supplierinfo']
        result = seller.get_warranty_return_partner()
        return result

    name = fields.Char('Customer description', required=True)
    claim_origine = fields.Selection(
            [('broken_down', 'Broken down product'),
             ('not_appropiate', 'Not appropiate product'),
             ('none', 'Not specified'),
             ('legal', 'Legal retractation'),
             ('cancellation', 'Order cancellation'),
             ('damaged', 'Damaged delivered product'),
             ('error', 'Shipping error'),
             ('exchange', 'Exchange request'),
             ('lost', 'Lost during transport'),
             ('other', 'Other')
             ],
            'Claim Subject', default='broken_down',
            required=True,
            help="To describe the line product problem")
    claim_descr = fields.Text(
            'Claim description',
            help="More precise description of the problem")
    product_id = fields.Many2one(
            'product.product',
            string='Product',
            help="Returned product")
    equivalent_product_id = fields.Many2one(
            'product.product', 'Replacement')
    product_returned_quantity = fields.Float(
            'Quantity', digits=(12, 2), default=1.0,
            help="Quantity of product returned")
    unit_sale_price = fields.Float(
            'Unit sale price', digits=(12, 2),
            help="Unit sale price of the product. Auto filled if retrun done "
                 "by invoice selection. Be careful and check the automatic "
                 "value as don't take into account previous refunds, invoice "
                 "discount, can be for 0 if product for free,...")
    return_value = fields.Float(
            compute="_line_total_amount", string='Total return',
            help="Quantity returned * Unit sold price")
    prodlot_id = fields.Many2one(
            'stock.production.lot',
            string='Serial/Lot n°',
            help="The serial/lot of the returned product")
    applicable_guarantee = fields.Selection(
            [('us', 'Company'),
             ('supplier', 'Supplier'),
             ('brand', 'Brand manufacturer')],
            'Warranty type')
    guarantee_limit = fields.Date(
            'Warranty limit',
            readonly=True,
            help="The warranty limit is computed as: invoice date + warranty "
                 "defined on selected product.")
    warning = fields.Char(
            'Warranty',
            readonly=True,
            help="If warranty has expired")
    warranty_type = fields.Selection(
            selection=get_warranty_return_partner,
            string='Warranty type',
            readonly=True,
            help="Who is in charge of the warranty return treatment towards "
                 "the end customer. Company will use the current company "
                 "delivery or default address and so on for supplier and brand"
                 " manufacturer. Does not necessarily mean that the warranty "
                 "to be applied is the one of the return partner (ie: can be "
                 "returned to the company and be under the brand warranty")
    warranty_return_partner = fields.Many2one(
            'res.partner',
            string='Warranty Address',
            help="Where the customer has to send back the product(s)")
    claim_id = fields.Many2one(
            'crm.claim', string='Related claim',
            help="To link to the case.claim object")
    state = fields.Selection(
            [('draft', 'Draft'),
             ('refused', 'Refused'),
             ('confirmed', 'Confirmed')],
            string='State', default='draft')
    substate_id = fields.Many2one(
            'substate.substate',
            string='Sub state',
            help="Select a sub state to precise the standard state. Example 1:"
                 " state = refused; substate could be warranty over, not in "
                 "warranty, no problem,... . Example 2: state = to treate; "
                 "substate could be to refund, to exchange, to repair,...")
    last_state_change = fields.Date(
            string='Last change',
            help="To set the last state / substate change")
    invoice_line_id = fields.Many2one(
            'account.invoice.line',
            string='Invoice Line',
            help='The invoice line related to the returned product')
    refund_line_id = fields.Many2one(
            'account.invoice.line',
            string='Refund Line',
            help='The refund line related to the returned product')

    move_in_customer_id = fields.Many2one(
            'stock.move',
            string='Move Line from customer picking in',
            help='The move line related to the returned product')
    move_out_customer_id = fields.Many2one(
            'stock.move',
            string='Move Line from customer picking out',
            help='The move line related to the returned product')

    move_in_customer_state = fields.Selection(
            related='move_in_customer_id.state',
            string='picking in state', readonly=True,
            selection=MOVE_STATE_SELECTION)
    move_out_customer_state = fields.Selection(
            related="move_out_customer_id.state",
            string='picking out state', readonly=True,
            selection=MOVE_STATE_SELECTION)
    repair_id = fields.Many2one('mrp.repair', 'Repair')
    repair_state = fields.Selection(related='repair_id.state',
                                    selection=REPAIR_SELECTION,
                                    string='repair state', readonly=True)
    supplier_id = fields.Many2one('res.partner', 'Supplier')

    supplier_line_id = fields.Many2one('claim.line', 'Supplier claim line')
    original_line_id = fields.Many2one('claim.line', 'original claim line', readonly=True)

    claim_type = fields.Many2one(related='claim_id.claim_type',
                                  string='Claim type', readonly=True)

    move_in_supplier_state = fields.Selection(
            related='supplier_line_id.move_in_customer_state',
            string='supplier picking in state', readonly=True,
            selection=MOVE_STATE_SELECTION)

    move_out_supplier_state = fields.Selection(
            related='supplier_line_id.move_out_customer_state',
            string='supplier picking out state', readonly=True,
            selection=MOVE_STATE_SELECTION)

    user_id = fields.Many2one("res.users",
            related='claim_id.user_id',
            string='Responsible', readonly=True,
            store=True)

    partner_id = fields.Many2one("res.partner",
            related='claim_id.partner_id',
            string='Customer', readonly=True,
            store=True)

    location_dest_id = fields.Many2one(
            'stock.location',
            string='Return Stock Location',
            help='The return stock location of the returned product')

    internal_description = fields.Text(string='Internal Description')

    @api.onchange('product_id')
    def _get_default_supplier(self):
        if self.product_id and len(self.product_id.seller_ids):
            self.supplier_id = self.product_id.seller_ids[0].name
            partners = self.product_id.seller_ids
        else:
            self.supplier_id = False
            partners = self.env['res.partner'].search([('supplier', '=', True)])
        return {'domain': {'partner_id': [('id', 'in', [x.id for x in partners])]}}

    @api.multi
    def auto_set_warranty(self):
        """ Set warranty automatically
        if the user has not himself pressed on 'Calculate warranty state'
        button, it sets warranty for him"""
        for line in self:
            if not line.warning:
                line.set_warranty()
        return True

    @api.multi
    def set_warranty(self):
        """ Calculate warranty limit and address """
        return True

    @api.multi
    def equivalent_products(self):
        view = self.env.ref('crm_claim_rma.equivalent_products_wizard')
        wiz = self.env['equivalent.products.wizard'].with_context(claim_line=self.id).create({'line_id': self.id})

        return {
            'name': _("Equivalent products"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': view.id,
            'view_type': 'form',
            'res_model': 'equivalent.products.wizard',
            'res_id': wiz.id,
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
        }


# TODO add the option to split the claim_line in order to manage the same
# product separately
class CrmClaim(models.Model):
    _inherit = "crm.claim"

    _rec_name = "number"

    @api.onchange('claim_type')
    def onchange_claim_type(self):
        customer_type = self.env.ref('crm_claim_type.crm_claim_type_customer')
        supplier_type = self.env.ref('crm_claim_type.crm_claim_type_supplier')
        if self.claim_type.id == customer_type.id:
            return {'domain': {'partner_id': [('customer', '=', True),
                                              ('is_company', '=', True)]}}
        elif self.claim_type.id == supplier_type.id:
            return {'domain': {'partner_id': [('supplier', '=', True),
                                              ('is_company', '=', True)]}}
        else:
            return {}

    def _get_sequence_number(self):
        seq_obj = self.env['ir.sequence']
        res = seq_obj.get('crm.claim.rma') or '/'
        return res

    @api.model
    def _get_default_warehouse(self):
        company_id = self.env.user.company_id.id
        wh_obj = self.env['stock.warehouse']
        wh_ids = wh_obj.search([('company_id', '=', company_id)])
        if not wh_ids:
            raise exceptions.UserError(
                _('There is no warehouse for the current user\'s company.'))
        return wh_ids[0]

    @api.model
    def create(self, vals):
        if ('number' not in vals) or (vals.get('number') == '/'):
            vals['number'] = self._get_sequence_number()
        new_id = super(CrmClaim, self).create(vals)
        return new_id

    @api.multi
    def copy_data(self, default=None):
        if default is None:
            default = {}
        std_default = {
            'invoice_ids': False,
            'picking_ids': False,
            'number': self._get_sequence_number(),
        }
        std_default.update(default)
        return super(CrmClaim, self).copy_data(default=std_default)

    number = fields.Char(
            'Number', readonly=True,
            required=True,
            index=False, default='/',
            help="Company internal claim unique number")
    categ_id = fields.Many2one('crm.claim.category', 'Category')
    supplier_number = fields.Char('Supplier Number',
                                  index=False,
                                  help="Supplier claim number")
    claim_type = fields.Many2one('crm.claim.type',
                                 string='Claim type',
                                 required=True,
                                 help="Customer: from customer to company.\n "
                                      "Supplier: from company to supplier.")
    claim_line_ids = fields.One2many('claim.line', 'claim_id',
                                     string='Return lines')
    planned_revenue = fields.Float('Expected revenue')
    planned_cost = fields.Float('Expected cost')
    real_revenue = fields.Float('Real revenue')
    real_cost = fields.Float('Real cost')
    invoice_ids = fields.One2many('account.invoice', 'claim_id', 'Refunds')
    picking_ids = fields.One2many('stock.picking', 'claim_id', 'RMA')
    invoice_id = fields.Many2one('account.invoice', string='Invoice',
                                 help='Related original Cusotmer invoice')
    delivery_address_id = fields.Many2one('res.partner', string='Partner delivery address',
                                          help="This address will be used to deliver repaired or replacement"
                                               "products.")
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse',
                                   required=True, default=_get_default_warehouse)
    state_show_buttons = fields.Boolean(related='stage_id.show_buttons',
                                        store=True, string="show buttons",
                                        readonly=True)
    rma_cost = fields.Float('RMA cost')
    invoice_type = fields.Selection([('invoice', 'Invoice'),
                                     ('refund', 'Refund')],
                                    'Invoice type', required=True,
                                    default='invoice')
    invoice_method = fields.Selection([('none', 'Not invoice'),
                                       ('b4repair', 'Before repair'),
                                       ('after_repair', 'After repair')],
                                      'Invoice method', default='none')

    _sql_constraints = [
        ('number_uniq', 'unique(number, company_id)',
         'Number/Reference must be unique per Company!'),
    ]

    @api.multi
    def write(self, vals):
        update_vals = {}
        if vals.get('partner_id', False) or vals.get('invoice_method', False):
            for claim in self:
                if vals.get('partner_id', False) and vals['partner_id'] != \
                        claim.partner_id.id:
                    update_vals['partner_id'] = vals['partner_id']
                if vals.get('invoice_method', False) and \
                        vals['invoice_method'] != claim.invoice_method:
                    update_vals['invoice_method'] = vals['invoice_method']
        res = super(CrmClaim, self).write(vals)
        if update_vals:
            for claim in self:
                for line in claim.claim_line_ids:
                    if line.repair_id and line.repair_id.state == 'draft':
                        line.repair_id.write(update_vals)
        return res

    @api.model
    def message_get_reply_to(self, res_ids, default=None):
        claims = self.sudo().browse(res_ids)
        aliases = self.env['crm.team'].message_get_reply_to(claims.mapped('team_id').ids, default=default)
        return {claim.id: aliases.get(claim.team_id.id or 0, False) for claim in claims}

    @api.multi
    def message_get_suggested_recipients(self):
        recipients = super(CrmClaim, self).message_get_suggested_recipients()
        try:
            for claim in self:
                if claim.partner_id:
                    self._message_add_suggested_recipient(recipients, claim, partner=claim.partner_id, reason=_('Customer'))
                elif claim.email_from:
                    self._message_add_suggested_recipient(recipients, claim, email=claim.email_from, reason=_('Customer Email'))
        except Exception:
            # no read access rights -> just ignore suggested recipients
            # because this imply modifying followers
            pass
        return recipients


class CrmClaimStage(models.Model):

    _inherit = "crm.claim.stage"

    show_buttons = fields.Boolean('Show buttons')
    closed = fields.Boolean('closed')
