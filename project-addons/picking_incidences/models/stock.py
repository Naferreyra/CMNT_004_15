##############################################################################
#
#    Copyright (C) 2015 Pexego Sistemas Informáticos All Rights Reserved
#    $Omar Castiñeira Saavedra <omar@pexego.es>$
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

from odoo import fields, models, api, _, exceptions
import odoo.addons.decimal_precision as dp
from odoo.tools.float_utils import float_compare, float_round
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import time


class StockMove(models.Model):

    _inherit = 'stock.move'

    qty_ready = fields.\
        Float('Qty ready', readonly=True, copy=False,
              digits=dp.get_precision('Product Unit of Measure'))
    qty_confirmed = fields.\
        Float('Qty confirmed', copy=False,
              digits=dp.get_precision('Product Unit of Measure'))

    @api.multi
    def _action_cancel(self):
        for move in self:
            if move.picking_id and move.picking_id.block_picking:
                raise exceptions.\
                    Warning(_("Cannot cancel this move because it is being "
                              "processed in Vstock."))
        return super()._action_cancel()


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    with_incidences = fields.Boolean('With incidences', readonly=True,
                                     copy=False)
    block_picking = fields.Boolean('Albarán procesado Vstock')
    partial_picking = fields.Boolean('Partial picking', default=False)

    state = fields.Selection(selection_add=[('partially_available', 'Partially Available')])

    @api.multi
    def _compute_show_check_availability(self):
        for picking in self:
            res = super(StockPicking, picking)._compute_show_check_availability()
            if not res and picking.state == 'partially_available':
                picking.show_check_availability = picking.is_locked

    @api.depends('move_type', 'move_lines.state', 'move_lines.picking_id')
    @api.one
    def _compute_state(self):
        super(StockPicking, self)._compute_state()
        if self.state not in ('draft', 'done', 'cancel'):
            relevant_move_state = self.move_lines._get_relevant_state_among_moves()
            if relevant_move_state == 'partially_available':
                self.state = 'partially_available'
            elif relevant_move_state == 'confirmed':
                if any(move.state == 'assigned' for move in self.move_lines):
                    self.state = 'partially_available'

    @api.multi
    def _create_backorder(self, backorder_moves=[]):
        bck_id = super(StockPicking, self)._create_backorder(backorder_moves=backorder_moves)
        if bck_id:
            self.write({'partial_picking': True, 'date_done': False})
        return bck_id

    @api.multi
    def _create_backorder_incidences(self, backorder_moves):
        """The original _create_backorder function just ignores backorder_moves"""
        backorders = self.env['stock.picking']
        for picking in self:
            if not backorder_moves:
                backorder_moves = picking.move_lines
            moves_to_backorder = backorder_moves.filtered(lambda x: x.state not in ('done', 'cancel'))
            if moves_to_backorder:
                backorder_picking = picking.copy({
                    'name': '/',
                    'move_lines': [],
                    'move_line_ids': [],
                    'backorder_id': picking.id
                })
                picking.message_post(
                    body=_('The backorder <a href=# data-oe-model=stock.picking data-oe-id=%d>%s</a> '
                           'has been created.') % (backorder_picking.id, backorder_picking.name))
                moves_to_backorder.write({'picking_id': backorder_picking.id})
                moves_to_backorder.mapped('move_line_ids').write({'picking_id': backorder_picking.id})
                backorder_picking.action_assign()
                backorder_picking.write({'partial_picking': True, 'date_done': False})
                backorders |= backorder_picking
        return backorders

    @api.multi
    def action_accept_ready_qty(self):
        self.ensure_one()
        self.with_incidences = False
        new_moves = []
        for move in self.move_lines:
            if move.state in ('done', 'cancel'):
                # ignore stock moves cancelled or already done
                continue
            precision = move.product_uom.rounding
            remaining_qty = move.product_uom_qty - move.qty_ready
            remaining_qty = float_round(remaining_qty,
                                        precision_rounding=precision)
            if not move.qty_ready:
                new_moves.append(move.id)
            elif float_compare(remaining_qty, 0, precision_rounding=precision) > 0 and \
                    float_compare(remaining_qty, move.product_qty, precision_rounding=precision) < 0:
                move_ctx = move._context.copy()
                move_ctx.update(accept_ready_qty=True)
                new_move = move.with_context(move_ctx)._split(remaining_qty)
                new_moves.append(new_move)
        if new_moves:
            new_moves = self.env['stock.move'].browse(new_moves)
            bcko = self._create_backorder_incidences(new_moves)
            new_moves.write({'qty_ready': 0.0})
            #self.do_unreserve()
            #self.action_assign()
            #self.recheck_availability()
        self.message_post(body=_("User %s accepted ready quantities.") %
                          (self.env.user.name))
        self.action_done()
        self.date_done = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    @api.multi
    def action_assign(self):
        res = super(StockPicking, self).action_assign()
        for pick in self:
            pick.with_incidences = False
        return res

    @api.multi
    def action_done(self):
        for pick in self:
            if pick.with_incidences:
                raise exceptions.Warning(_("Cannot process picking with "
                                           "incidences. Please fix or "
                                           "ignore it."))
        return super(StockPicking, self).action_done()

    @api.onchange('move_type')
    def onchange_move_type(self):
        if self.move_type == "direct":
            for line in self.move_lines:
                line.qty_confirmed = line.reserved_availability
        else:
            for line in self.move_lines:
                line.qty_confirmed = 0.0

    @api.multi
    def action_cancel(self):
        for pick in self:
            if pick.with_incidences and pick.picking_type_code == 'incoming':
                raise exceptions.\
                    Warning(_("Cannot cancel an incoming picking with "
                              "incidences. You can only process it."))
            if pick.block_picking:
                raise exceptions.\
                    Warning(_("Cannot cancel this picking because it is being "
                              "processed in Vstock."))
        return super(StockPicking, self).action_cancel()

    @api.multi
    def action_copy_reserv_qty(self):
        for pick in self:
            for move in pick.move_lines:
                move.qty_confirmed = move.reserved_availability

    @api.multi
    def action_accept_confirmed_qty(self):
        for pick in self:
            #check move lines confirmed qtys
            for move in pick.move_lines:
                if move.qty_confirmed > move.reserved_availability:
                    raise exceptions.\
                        Warning(_("Cannot assign more qty that reserved "
                                  "availability."))
            new_moves = []
            for move in pick.move_lines:
                if move.state in ('done', 'cancel'):
                    # ignore stock moves cancelled or already done
                    continue
                precision = move.product_uom.rounding
                remaining_qty = move.product_uom_qty - move.qty_confirmed
                remaining_qty = float_round(remaining_qty,
                                            precision_rounding=precision)
                if not move.qty_confirmed:
                    new_moves.append(move.id)
                elif float_compare(remaining_qty, 0,
                                   precision_rounding=precision) > 0 and \
                    float_compare(remaining_qty, move.product_qty,
                                  precision_rounding=precision) < 0:
                    new_move = move._split(remaining_qty)
                    new_moves.append(new_move)
                if not move.product_uom_qty:
                    move.state = 'draft'
                    move.unlink()
            if new_moves:
                new_moves = self.env['stock.move'].browse(new_moves)
                bck = self._create_backorder_incidences(new_moves)
                bck.write({'move_type': 'one'})
                self.action_assign()
                pick.move_lines.write({'state': 'assigned'})
            self.message_post(body=_("User %s accepted confirmed qties.") %
                              self.env.user.name)

    @api.model
    def cron_accept_qty_incoming_shipments(self):
        pickings_ref = ''
        template = self.env.ref('picking_incidences.alert_cron_accept_qty_incoming_shipments', False)
        picking_category = self.env.ref('stock.picking_type_in').id
        location_supplier = self.env.ref('stock.stock_location_suppliers').id
        picking_list = self.env['stock.picking'].search([('picking_type_id', '=', picking_category),
                                                         ('state', 'in', ['assigned', 'partially_available']),
                                                         ('location_id', '=', location_supplier),
                                                         ('with_incidences', '=', True)])
        for picking in picking_list:
            picking.action_accept_ready_qty()
            pickings_ref += '\n' + picking.name

        if picking_list:
            ctx = dict(self._context)
            ctx.update({
                'default_model': 'stock.picking',
                'default_res_id': picking_list[0].id,
                'default_use_template': bool(template.id),
                'default_template_id': template.id,
                'default_composition_mode': 'comment',
                'mark_so_as_sent': True,
                'pickings_name': pickings_ref
            })
            composer_id = self.env['mail.compose.message'].with_context(ctx).create({})
            composer_id.with_context(ctx).send_mail()

        return True

