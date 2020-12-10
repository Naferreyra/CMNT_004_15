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

from openerp import models, fields, api


class StockReserve(models.Model):

    _inherit = 'stock.reservation'

    mrp_id = fields.Many2one('mrp.production', 'Production')


class StockPicking(models.Model):

    _inherit = "stock.picking"

    @api.one
    def _get_if_productions(self):
        with_prods = False
        for line in self.move_lines:
            if line.sale_line_id and line.sale_line_id.mrp_production_ids:
                with_prods = True
                break
        self.with_productions = with_prods

    with_productions = fields.Boolean("With productions", readonly=True,
                                      compute='_get_if_productions')

    @api.multi
    def write(self, vals):
        res = super(StockPicking, self).write(vals)
        production_obj = self.env['mrp.production']
        for picking in self:
            if picking.origin and 'MO' in picking.origin and vals.get('date_done', False) and picking.state == 'done':
                mrp_product = production_obj.search([('name', '=', picking.origin)])
                if mrp_product and mrp_product.picking_out.id == picking.id:
                    # Create in picking
                    pick_in = picking.create({'partner_id': picking.partner_id.id,
                                              'picking_type_id': self.env.ref('stock.picking_type_in').id,
                                              'location_id': mrp_product.move_finished_ids and
                                                             mrp_product.move_finished_ids[0].location_id.id,
                                              'location_dest_id': mrp_product.move_finished_ids and
                                                                  mrp_product.move_finished_ids[0].location_dest_id.id,
                                              'origin': picking.origin})
                    # Update reference in_picking
                    mrp_product.picking_in = pick_in.id
                    cost_moves = sum(picking.move_lines.mapped('price_unit'))
                    production = production_obj.search([('name', '=', picking.origin)])
                    production.move_finished_ids.write({'price_unit': -cost_moves,
                                                        'picking_id': pick_in.id})
                    production.move_finished_ids.mapped('move_line_ids').write({'picking_id': pick_in.id})
                    pick_in.action_assign()
                elif mrp_product.picking_in.id == picking.id:
                    mrp_product.button_mark_done()
        return res


