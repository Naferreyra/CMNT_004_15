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
from odoo import fields, models, _, exceptions, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import time

#TODO: revisar este wizard al migrar crm_claim_rma_custom
class ClaimMakePicking(models.TransientModel):

    _name = "claim_make_picking.wizard"
    _description = 'Wizard to create pickings from claim lines'

    # Get default destination location
    @api.model
    def _get_dest_loc(self):
        """Return the location_id to use as destination.
        If it's an outoing shippment: take the customer stock property
        If it's an incoming shippment take the location_dest_id common to all
        lines, or if different, return None."""
        context = self.env.context
        loc_id = False
        supplier_type = self.env.ref('crm_claim_type.crm_claim_type_supplier').id
        customer_type = self.env.ref('crm_claim_type.crm_claim_type_customer').id
        if context.get('picking_type') == 'out':
            partner = self.env['res.partner'].browse(context.get('partner_id'))
            if context.get('type') == supplier_type:
                loc_id = partner.property_stock_supplier
            elif context.get('type') == customer_type:
                loc_id = partner.property_stock_customer
        elif context.get('picking_type') == 'in':
            # Add the case of return to supplier !
            line_ids = self._get_claim_lines()
            loc_id = self._get_common_dest_location_from_line(line_ids)
        return loc_id

    @api.model
    def _get_claim_lines(self):
        # TODO use custom states to show buttons of this wizard or not instead
        # of raise an error
        context = self.env.context
        line_obj = self.env['claim.line']
        if context.get('picking_type') == 'out':
            move_field = 'move_out_customer_id'
        else:
            move_field = 'move_in_customer_id'
        good_lines = []
        line_ids = line_obj.search([('claim_id', '=', context['active_id'])])
        for line in line_ids:
            if not line[move_field] or line[move_field].state == 'cancel':
                good_lines.append(line.id)
        if not good_lines:
            raise exceptions.UserError(
                _('A picking has already been created for this claim.'))
        return good_lines

    # Get default source location
    def _get_source_loc(self):
        loc_id = False
        context = self.env.context
        supplier_type = self.env.ref('crm_claim_type.crm_claim_type_supplier').id
        customer_type = self.env.ref('crm_claim_type.crm_claim_type_customer').id
        if context.get('picking_type') == 'out':
            warehouse = self.env['stock.warehouse'].browse(context.get('warehouse_id'))
            if context.get('type') == supplier_type:
                loc_id = warehouse.lot_breakdown_id
            if context.get('type') == customer_type:
                loc_id = warehouse.lot_rma_id

        elif context.get('picking_type') == 'in':
            partner = self.env['res.partner'].browse(context.get('partner_id'))
            if context.get('type') == supplier_type:
                loc_id = partner.property_stock_supplier

            if context.get('type') == customer_type:
                loc_id = partner.property_stock_customer
        return loc_id

    claim_line_source_location = fields.Many2one(
            'stock.location',
            string='Source Location',
            help="Location where the returned products are from.",
            required=True, default=_get_source_loc)
    claim_line_dest_location = fields.Many2one(
            'stock.location',
            string='Dest. Location',
            help="Location where the system will stock the returned products.",
            required=True, default=_get_dest_loc)
    claim_line_ids = fields.Many2many(
            'claim.line',
            'claim_line_picking',
            'claim_picking_id',
            'claim_line_id',
            string='Claim lines', default=_get_claim_lines)

    def _get_common_dest_location_from_line(self, line_ids):
        """Return the ID of the common location between all lines. If no common
        destination was  found, return False"""
        loc_id = False
        line_obj = self.env['claim.line']
        line_location = []
        for line in line_obj.browse(line_ids):
            if line.location_dest_id.id not in line_location:
                line_location.append(line.location_dest_id.id)
        if len(line_location) == 1:
            loc_id = line_location
        return loc_id

    def _get_common_partner_from_line(self, line_ids):
        """Return the ID of the common partner between all lines. If no common
        partner was found, return False"""
        partner_id = False
        line_obj = self.env['claim.line']
        line_partner = []
        for line in line_obj.browse(line_ids):
            if (line.warranty_return_partner
                    and line.warranty_return_partner.id
                    not in line_partner):
                line_partner.append(line.warranty_return_partner.id)
        if len(line_partner) == 1:
            partner_id = line_partner[0]
        return partner_id

    @api.model
    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def create_move(self, claim_line, p_type, picking_id, claim, note, write_field):
        reserv_obj = self.env['stock.reservation']
        type_ids = self.env['stock.picking.type'].search([('code', '=', p_type)])
        partner_id = claim.delivery_address_id
        move_obj = self.env['stock.move']
        product = claim_line.product_id
        if self.env.context.get('picking_type', 'in') == u'out' and \
                claim_line.equivalent_product_id:
            product = claim_line.equivalent_product_id
        qty = claim_line.product_returned_quantity

        move_id = move_obj.create(
            {'name': claim_line.product_id.name,
             'priority': '0',
             'date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
             'date_expected': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
             'product_id': product.id,
             'picking_type_id': type_ids and type_ids[0].id,
             'product_uom_qty': claim_line.product_returned_quantity,
             'product_uom': claim_line.product_id.uom_id.id,
             'partner_id': partner_id.id,
             'picking_id': picking_id.id,
             'state': 'draft',
             'price_unit': claim_line.unit_sale_price,
             'company_id': claim.company_id.id,
             'location_id': self.claim_line_source_location.id,
             'location_dest_id': self.claim_line_dest_location.id,
             'note': note,
             'claim_line_id': claim_line.id
             })
        # In Italy, need to make the purchase order first if there is not stock available
        location_stock = self.env.ref('stock.stock_location_stock')
        if picking_id.origin.startswith('IT-RMA') \
                and picking_id.location_id == location_stock:
            qty_on_stock = product.with_context(location=location_stock.id).qty_available
            if not qty_on_stock \
                    or qty_on_stock \
                    and (qty_on_stock - product.outgoing_qty) < move_id.product_uom_qty:
                move_id.procure_method = 'make_to_order'
        if p_type == 'outgoing' and claim_line.product_id.type == 'product':
            reserv_vals = {
                'product_id': product.id,
                'product_uom': claim_line.product_id.uom_id.id,
                'product_uom_qty': claim_line.product_returned_quantity,
                'date_validity': False,
                'name': u"{}".format(claim_line.claim_id.number),
                'location_id': self.claim_line_source_location.id,
                'location_dest_id': self.claim_line_dest_location.id,
                'move_id': move_id.id,
                'claim_id': claim_line.claim_id.id,
            }
            reserve = reserv_obj.create(reserv_vals)
            reserve.reserve()
        claim_line.write({write_field: move_id.id})

    # If "Create" button pressed
    def action_create_picking(self):
        picking_obj = self.env['stock.picking']
        claim_obj = self.env['crm.claim']
        view_obj = self.env['ir.ui.view']
        name = 'RMA picking out'
        context = self.env.context
        if context.get('picking_type') == 'out':
            p_type = 'outgoing'
            write_field = 'move_out_customer_id'
            note = 'RMA picking out'
            view_xml_id = 'stock_picking_form'
        else:
            p_type = 'incoming'
            write_field = 'move_in_customer_id'
            if context.get('picking_type'):
                note = 'RMA picking ' + str(context.get('picking_type'))
                name = note
        model = 'stock.picking'
        view_id = view_obj.search([('model', '=', model),
                                   ('type', '=', 'form'),
                                   ])[0]
        claim = claim_obj.browse(context['active_id'])
        partner_id = claim.delivery_address_id
        line_ids = [x.id for x in self.claim_line_ids]
        # In case of product return, we don't allow one picking for various
        # product if location are different
        # or if partner address is different
        if context.get('product_return'):
            common_dest_loc_id = self._get_common_dest_location_from_line(line_ids)
            self.env['claim.line'].browse(line_ids).auto_set_warranty()
            common_dest_partner_id = self._get_common_partner_from_line(line_ids)
        # create picking
        type_ids = self.env['stock.picking.type'].search([('code', '=', p_type)])
        picking_id = picking_obj.create(
            {'origin': claim.number,
             'picking_type_id': type_ids and type_ids[0].id,
             'move_type': 'one',  # direct
             'state': 'draft',
             'date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
             'partner_id': partner_id.id,
             'invoice_state': "none",
             'company_id': claim.company_id.id,
             'location_id': self.claim_line_source_location.id,
             'location_dest_id': self.claim_line_dest_location.id,
             'note': note,
             'claim_id': claim.id,
             })
        # Create picking lines
        for wizard_claim_line in self.claim_line_ids:
            self.create_move(wizard_claim_line, p_type, picking_id, claim, note, write_field)

        if picking_id:
            picking_id.action_assign()
            # if we validate the picking, it fails because there is no quantity available
            #picking_id.button_validate()
            domain = ("[('picking_type_code', '=', '%s'), \
                                   ('partner_id', '=', %s)]" %
                      (p_type, partner_id.id))

            return {
                'name': '%s' % name,
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': view_id.id,
                'domain': domain,
                'res_model': model,
                'res_id': picking_id.id,
                'type': 'ir.actions.act_window',
            }
        else:
            return {'type': 'ir.actions.act_window_close'}
