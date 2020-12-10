##############################################################################
#
#    Copyright (C) 2014 Pexego All Rights Reserved
#    $Jesús Ventosinos Mayor <jesus@pexego.es>$
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

from odoo import models, api, _, fields
from odoo.exceptions import ValidationError, Warning


class StockLocation(models.Model):

    _inherit = "stock.location"

    def get_quantity_source_location(self, location_id, product_id):
        ctx = dict(self.env.context)
        ctx.update({'location': location_id.id})
        product = self.env['product.product'].with_context(ctx).\
            browse(product_id)
        qty = product.qty_available
        return qty

    def move_pantry_kitchen(self, product_id, qty, check_qty, assign=True):
        self.location_move(product_id, 'stock_location_pantry', qty,
                           'stock_location_kitchen', False, check_qty, assign)

    def move_kitchen_cooked(self, product_id, qty, check_qty, assign=True):
        self.location_move(product_id, 'stock_location_kitchen', qty,
                           'stock.stock_location_stock', True, check_qty,
                           assign)

    def move_kitchen_nursing(self, product_id, qty, check_qty, assign=True):
        self.location_move(product_id, 'stock_location_kitchen', qty,
                           'stock_location_nursing', False, check_qty, assign)

    def move_stock_nursing(self, product_id, qty, check_qty, assign=True):
        self.location_move(product_id, 'stock.stock_location_stock', qty,
                           'stock_location_nursing', False, check_qty, assign)

    def move_nursing_damaged(self, product_id, qty, check_qty, assign=True):
        self.location_move(product_id, 'stock_location_nursing', qty,
                           'stock_location_damaged', False, check_qty, assign)

    def move_nursing_cooked(self, product_id, qty, check_qty, assign=True):
        self.location_move(product_id, 'stock_location_nursing', qty,
                           'stock.stock_location_stock', True, check_qty,
                           assign)

    def move_quality_cooked(self, product_id, qty, check_qty, assign=True):
        self.location_move(product_id, 'stock_location_quality', qty,
                           'stock.stock_location_stock', True, check_qty,
                           assign)

    def move_cooked_damaged(self, product_id, qty, check_qty, assign=True):
        self.location_move(product_id, 'stock.stock_location_stock', qty,
                           'stock_location_damaged', False, check_qty, assign)

    def move_beach_stock(self, product_id, qty, check_qty, assign=False):
        self.location_move(product_id, 'stock.stock_location_company', qty,
                           'stock.stock_location_stock', True, check_qty,
                           assign)

    def move_beach_kitchen(self, product_id, qty, check_qty, assign=True):
        self.location_move(product_id, 'stock.stock_location_company', qty,
                           'stock_location_kitchen', False, check_qty, assign)

    def move_beach_pantry(self, product_id, qty, check_qty, assign=True):
        self.location_move(product_id, 'stock.stock_location_company', qty,
                           'stock_location_pantry', False, check_qty, assign)

    def move_stock_kitchen(self, product_id, qty, check_qty, assign=True):
        self.location_move(product_id, 'stock.stock_location_stock', qty,
                           'stock_location_kitchen', False, check_qty, assign)

    def move_stock_pantry(self, product_id, qty, check_qty, assign=True):
        self.location_move(product_id, 'stock.stock_location_stock', qty,
                           'stock_location_pantry', False, check_qty, assign)

    def move_marketing_stock(self, product_id, qty, check_qty, assign=True):
        self.location_move(product_id, 'stock_location_marketing', qty,
                           'stock.stock_location_stock', False, check_qty,
                           assign)

    def move_stock_marketing(self, product_id, qty, check_qty, assign=True):
        self.location_move(product_id, 'stock.stock_location_stock', qty,
                           'stock_location_marketing', False, check_qty, assign)

    def move_product_stock(self, product_id, qty, check_qty, assign=True):
        self.location_move(product_id, 'stock_location_product', qty,
                           'stock.stock_location_stock', False, check_qty,
                           assign)

    def move_marketing_product(self, product_id, qty, check_qty, assign=True):
        self.location_move(product_id, 'stock_location_marketing', qty,
                           'stock_location_product', False, check_qty,
                           assign)

    def move_stock_product(self, product_id, qty, check_qty, assign=True):
        self.location_move(product_id, 'stock.stock_location_stock', qty,
                           'stock_location_product', False, check_qty, assign)

    def move_development_stock(self, product_id, qty, check_qty, assign=True):
        self.location_move(product_id, 'stock_location_development', qty,
                           'stock.stock_location_stock', False, check_qty,
                           assign)

    def move_stock_development(self, product_id, qty, check_qty, assign=True):
        self.location_move(product_id, 'stock.stock_location_stock', qty,
                           'stock_location_development', False, check_qty,
                           assign)

    def move_cooked_quality(self, product_id, qty, check_qty, assign=True):
        self.location_move(product_id, 'stock.stock_location_stock', qty,
                           'stock_location_quality', False, check_qty,
                           assign)

    def move_sat_stock(self, product_id, qty, check_qty, assign=True):
        self.location_move(product_id, 'stock_location_sat', qty,
                           'stock.stock_location_stock', True, check_qty,
                           assign)

    def move_stock_sat(self, product_id, qty, check_qty, assign=True):
        self.location_move(product_id, 'stock.stock_location_stock', qty,
                           'stock_location_sat', False, check_qty, assign)




    def location_move(self, product_id, source_location, qty, dest_location,
                      send_message=False, check_qty=False, assign=True):

        product = self.env['product.product'].browse(product_id)
        source_location = '.' in source_location and \
            source_location or 'location_moves.' + source_location
        dest_location = '.' in dest_location and \
            dest_location or 'location_moves.' + dest_location
        source_location = self.env.ref(source_location)
        dest_location = self.env.ref(dest_location)

        if check_qty:
            if qty > self.\
                    get_quantity_source_location(source_location, product_id):
                raise Warning("Check qty in source location")

        type_id = self.env.ref('stock.picking_type_internal')
        pick_vals = {
            'partner_id': self.env.user.company_id.partner_id.id,
            'picking_type_id': type_id.id,
            'location_id': source_location.id,
            'location_dest_id': dest_location.id
        }
        picking = self.env['stock.picking'].create(pick_vals)
        move_template = {
            'name': product.name,
            'product_id': product.id,
            'picking_type_id': type_id.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': qty,
            'location_id': source_location.id,
            'location_dest_id': dest_location.id,
            'picking_id': picking.id,
            'partner_id': picking.partner_id.id,
            'state': 'draft',
            'company_id': self.env.user.company_id.id,
        }
        new_move = self.env['stock.move'].create(move_template)
        if send_message:
            self.reassign_reservation_dates(product, [new_move])
        picking.action_assign()
        if assign:
            picking.action_done()

    @api.model
    def reassign_reservation_dates(self, product_id, moves):
        uom_obj = self.env['product.uom']
        product_uom = product_id.uom_id
        reservations = self.env['stock.reservation'].search(
            [('product_id', '=', product_id.id),
             ('state', 'in', ['confirmed', 'partially_available'])])
        reservation_index = 0

        reservation_used = 0
        for move in moves:
            qty_used = 0
            product_uom_qty = move.product_uom._compute_quantity(move.product_uom_qty, product_uom)
            while qty_used < product_uom_qty and reservation_index < \
                    len(reservations):
                reservation = reservations[reservation_index]
                reservation_qty = reservation.product_uom_qty - \
                    reservation.reserved_availability
                reservation_qty = reservation.product_uom._compute_quantity(reservation_qty, product_uom)
                if reservation_qty - reservation_used <= product_uom_qty - \
                        qty_used:
                    reservation.date_planned = move.date_expected
                    reservation_index += 1
                else:
                    reservation_used += product_uom_qty - qty_used
                    break
                qty_used += reservation_qty - reservation_used
                reservation_used = 0
        while reservation_index < len(reservations):
            reservations[reservation_index].date_planned = False
            reservation_index += 1


class StockMove(models.Model):

    _inherit = "stock.move"

    location_usage = fields.Selection([('supplier', 'Vendor Location'),
                                       ('view', 'View'),
                                       ('internal', 'Internal Location'),
                                       ('customer', 'Customer Location'),
                                       ('inventory', 'Inventory Loss'),
                                       ('procurement', 'Procurement'),
                                       ('production', 'Production'),
                                       ('transit', 'Transit Location')],
                                      related="location_id.usage",
                                      readonly=True)
    picking_type_code = fields.Selection([('incoming', 'Suppliers'),
                                          ('outgoing', 'Customers'),
                                          ('internal', 'Internal')],
                                         related="picking_type_id.code",
                                         readonly=True)

    @api.multi
    def unit_to_quality(self):
        wzd_obj = self.env["quality.move.wzd"]
        for move in self:
            wzd = wzd_obj.create({'qty': 1.0})
            wzd.with_context(active_id=move.id).action_move()
        return True
