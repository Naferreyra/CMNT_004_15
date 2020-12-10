##############################################################################
#
#    Copyright (C) 2014 Pexego Sistemas Informáticos All Rights Reserved
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


from odoo import models, fields, api, exceptions, _
from odoo.exceptions import except_orm, UserError


class MoveDetails(models.TransientModel):

    _name = 'picking.wizard.move.details'

    product_id = fields.Many2one('product.product', 'Product')
    qty = fields.Float('Quantity')
    move_id = fields.Many2one('stock.move', 'Move')
    wizard_id = fields.Many2one('picking.from.moves.wizard', 'wizard')


class CreatePickingMove(models.TransientModel):

    _name = 'picking.from.moves.wizard'

    @api.model
    def _get_lines(self):
        wiz_lines = []
        move_ids = self.env.context.get('active_ids', [])
        for move in self.env['stock.move'].browse(move_ids):
            if move.state != u'draft' or move.picking_id:
                continue
            wiz_lines.append({'product_id': move.product_id.id,
                              'qty': move.product_uom_qty,
                              'move_id': move.id})
        return wiz_lines

    date_picking = fields.Datetime('Date planned', required=True)
    move_detail_ids = fields.One2many('picking.wizard.move.details',
                                      'wizard_id', 'lines', default=_get_lines)
    container_id = fields.Many2one("stock.container", "Container")

    supplier_mode = fields.Boolean("Create pickings grouped by supplier", help="If this field is checked, the pickings will be created grouped by supplier. Otherwise the pickings will be created grouped by order")

    def _view_picking(self):
        action = self.env.ref('stock.action_picking_tree').read()[0]
        pick_ids = self.env.context.get('picking_ids', [])
        # override the context to get rid of the default filtering on picking type
        action['context'] = {}
        # choose the view_mode accordingly
        if len(pick_ids) > 1:
            action['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        else:
            res = self.env.ref('stock.view_picking_form').id
            action['views'] = [(res, 'form')]
            action['res_id'] = pick_ids and pick_ids[0] or False
        return action

    @api.multi
    def action_create_picking(self):
        context = self.env.context
        if not context.get('active_ids', False):
            return
        type_ids = self.env['stock.picking.type'].search([('code', '=', 'incoming')])
        if not type_ids:
            raise exceptions.except_orm(_('Picking error'), _('Type not found'))
        type_id = type_ids[0]
        moves = self.env['stock.move']
        all_moves = dict(self.env['stock.move'])
        # se recorren los movimientos para agruparlos por tipo
        for move in self.move_detail_ids.filtered(lambda m: not m.move_id.picking_id):
            if move.move_id.product_id.default_code == "----- PTE NOMBRE -----":
                raise UserError(
                    _("A picking cannot be created with a product called \"") + move.move_id.product_id.default_code + "\"")
            if self.container_id \
                    and move.move_id.container_id \
                    and self.container_id.id != move.move_id.container_id.id:
                move.move_id.container_id = False
            if not move.move_id.picking_type_id:
                move.move_id.picking_type_id = type_id
            else:
                type_id = move.move_id.picking_type_id
            if move.qty != move.move_id.product_uom_qty:
                if not move.qty:
                    continue
                if move.qty > move.move_id.product_uom_qty:
                    raise exceptions.except_orm(_('Quantity error'), _('The quantity is greater than the original.'))
                new_move = move.move_id.copy({'product_uom_qty': move.qty})
                new_move.purchase_line_id = move.move_id.purchase_line_id

                move.move_id.product_uom_qty = move.move_id.product_uom_qty - move.qty
                moves += new_move
                if self.supplier_mode:
                    if new_move.partner_id.id in all_moves:
                        all_moves[new_move.partner_id.id] += new_move
                    else:
                        all_moves[new_move.partner_id.id] = new_move
                else:
                    if new_move.purchase_line_id.order_id.id in all_moves:
                        all_moves[new_move.purchase_line_id.order_id.id] += new_move
                    else:
                        all_moves[new_move.purchase_line_id.order_id.id] = new_move
                if self.container_id and not move.move_id.container_id:
                    new_move.container_id = self.container_id.id
                elif not self.container_id:
                    move.move_id.date_expected = self.date_picking
            else:
                if self.container_id and not move.move_id.container_id:
                    move.move_id.container_id = self.container_id.id
                elif not self.container_id:
                    move.move_id.date_expected = self.date_picking
                moves += move.move_id
                if self.supplier_mode:
                    if move.move_id.partner_id.id in all_moves:
                        all_moves[move.move_id.partner_id.id] += move.move_id
                    else:
                        all_moves[move.move_id.partner_id.id] = move.move_id
                else:
                    if move.move_id.purchase_line_id.order_id.id in all_moves:
                        all_moves[move.move_id.purchase_line_id.order_id.id] += move.move_id
                    else:
                        all_moves[move.move_id.purchase_line_id.order_id.id] = move.move_id

        partners = moves.mapped('partner_id.id')
        pickings = []
        if all_moves:
            for (key, value) in all_moves.items():
                picking_vals = {
                    'picking_type_id': type_id.id,
                    'move_lines': [(6, 0, [x.id for x in value])],
                    'origin': ', '.join(value.mapped('purchase_line_id.order_id.name')),
                    'scheduled_date': self.date_picking,
                    'location_id': type_id.default_location_src_id.id,
                    'location_dest_id': type_id.default_location_dest_id.id,
                    'temp': True
                }
                if self.supplier_mode and key in partners:
                    picking_vals['partner_id'] = key
                else:
                    picking_vals['partner_id'] = all_moves[key][0].partner_id.id
                picking_id = self.env['stock.picking'].create(picking_vals)
                picking_id.action_confirm()
                # We don't use all_moves because when it is a kit, one of the moves is deleted and several ones are created instead
                picking_id.move_lines._force_assign()
                pickings.append(picking_id.id)
            context2 = dict(context)
            context2['picking_ids'] = pickings
            return self.with_context(context2)._view_picking()
        else:
            raise UserError(_("Picking already created"))
