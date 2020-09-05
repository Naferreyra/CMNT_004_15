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

from odoo import api, fields, models, exceptions


class StockPicking(models.Model):

    _inherit = "stock.picking"

    claim_id = fields.Many2one('crm.claim', 'Claim')


# This part concern the case of a wrong picking out. We need to create a new
# stock_move in a picking already open.
# In order to don't have to confirm the stock_move we override the create and
# confirm it at the creation only for this case
class StockMove(models.Model):

    _inherit = "stock.move"

    claim_line_id = fields.Many2one('claim.line', 'Claim Line')

    @api.multi
    def _action_done(self):
        res = super(StockMove, self)._action_done()
        for move in self:
            if move.claim_line_id:
                claim_line_obj = move.claim_line_id
                qty = claim_line_obj.product_returned_quantity
                loc_lost = self.env.ref('crm_rma_advance_location.stock_location_carrier_loss')
                claim_obj = claim_line_obj.claim_id
                if claim_line_obj.equivalent_product_id:
                    rma_cost = claim_obj.rma_cost
                    if move.location_dest_id == loc_lost:
                        standard_price = claim_line_obj.product_id.standard_price
                        rma_cost += (move.picking_type_code == u'incoming') and (standard_price * qty) or 0.0
                    else:
                        standard_price = claim_line_obj.equivalent_product_id.standard_price
                        rma_cost += (move.picking_type_code == u'outgoing') and (standard_price * qty) or 0.0
                    claim_obj.rma_cost = rma_cost
                elif move.location_dest_id == loc_lost:
                    standard_price = claim_line_obj.product_id.standard_price
                    rma_cost = claim_obj.rma_cost
                    rma_cost += (move.picking_type_code == u'incoming') and (standard_price * qty) or 0.0
                    claim_obj.rma_cost = rma_cost
        return res

    @api.model
    def create(self, vals):
        move_id = super(StockMove, self).create(vals)
        if vals.get('picking_id'):
            picking = self.env['stock.picking'].browse(vals['picking_id'])
            if picking.claim_id and picking.picking_type_code == u'incoming':
                move_id.state = 'confirmed'
        return move_id

    @api.multi
    def write(self, vals):
        for pick in self:
            if pick.picking_type_id.code == 'incoming':
                if 'date_expected' in vals.keys():
                    reservations = self.env['stock.reservation'].search(
                        [('product_id', '=', pick.product_id.id),
                         ('state', 'in', ['confirmed',
                                          'partially_available'])])
                    for reservation in reservations:
                        reservation.date_planned = pick.date_expected
                        if not reservation.claim_id:
                            continue
        return super(StockMove, self).write(vals)
