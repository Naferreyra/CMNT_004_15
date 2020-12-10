##############################################################################
#
#    Copyright (C) 2016 Comunitea Servicios Tecnológicos S.L.
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


from odoo import models, fields, api


class CancelMovesLinesWizard(models.TransientModel):

    _name = 'cancel.moves.lines.wzd'

    product_id = fields.Many2one('product.product', 'Product')
    origin = fields.Char()
    qty = fields.Float('Quantity')
    move_id = fields.Many2one('stock.move', 'Move')
    container_id = fields.Many2one('stock.container', 'Move')
    wizard_id = fields.Many2one('cancel.moves.wzd', 'wizard')


class CancelMovesWizard(models.TransientModel):

    _name = 'cancel.moves.wzd'

    @api.model
    def _get_lines(self):
        wiz_lines = []
        move_ids = self.env.context.get('active_ids', [])
        for move in self.env['stock.move'].browse(move_ids):
            if move.state != u'draft' or move.picking_id:
                continue
            wiz_lines.append({'product_id': move.product_id.id,
                              'qty': move.product_uom_qty,
                              'move_id': move.id,
                              'origin': move.origin,
                              'container_id': move.container_id})
        return wiz_lines


    move_detail_ids = fields.One2many('cancel.moves.lines.wzd',
                                      'wizard_id', 'lines', default=_get_lines)

    @api.multi
    def action_cancel_moves(self):
        self.move_detail_ids.mapped('move_id')._action_cancel()
