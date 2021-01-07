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

from odoo import models, fields, api, _, exceptions


class StockContainer(models.Model):

    _name = 'stock.container'
    _order = 'write_date desc'

    @api.multi
    def _set_date_expected(self):
        for container in self:
            if container.move_ids:
                date_expected = container.date_expected
                container.move_ids.write({'date_expected': date_expected})
                picking_ids = container.move_ids.mapped('picking_id')
                if picking_ids:
                    picking_ids.write({'scheduled_date': date_expected})
        return True

    @api.multi
    @api.depends('move_ids.picking_id.scheduled_date')
    def _get_date_expected(self):
        for container in self:
            if container.move_ids:
                max_date = max(container.move_ids.mapped('date_expected') or fields.Date.today())
                if max_date:
                    container.date_expected = max_date
                    container.move_ids.write({'date_expected': max_date})
            if not container.date_expected:
                container.date_expected = fields.Date.today()

    @api.multi
    def _get_picking_ids(self):
        for container in self:
            res = []
            for line in container.move_ids:
                if line.picking_id.id not in res:
                    res.append(line.picking_id.id)
                    container.picking_ids = res

    @api.multi
    def _get_responsible(self):
        for container in self:
            responsible = ''
            if container.picking_id:
                responsible = container.picking_id.commercial
            elif container.origin:
                responsible = self.env['sale.order'].search([('name', '=', container.origin)]).user_id
            container.user_id = responsible

    name = fields.Char("Container Ref.", required=True)
    date_expected = fields.Datetime("Date expected", compute='_get_date_expected', inverse='_set_date_expected', store=True,readonly=False, required=False)
    move_ids = fields.One2many("stock.move", "container_id", "Moves",
                               readonly=True, copy=False, domain=[('state', '!=', 'cancel')])
    picking_ids = fields.One2many('stock.picking', compute='_get_picking_ids', string='Pickings', readonly=True)

    user_id = fields.Many2one(string='Responsible', compute='_get_responsible')
    company_id = fields.Many2one("res.company", "Company", required=True,
                                 default=lambda self: self.env['res.company']._company_default_get('stock.container'))

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Container name must be unique')
    ]


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    usage = fields.Char(compute='_get_usage')
    shipping_identifier = fields.Char('Shipping identifier', size=64)
    temp = fields.Boolean("Temp.")
    container_ids = fields.Many2many('stock.container', string='Containers', compute='_get_containers')

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if not res.shipping_identifier and res.container_ids:
            res.shipping_identifier = ''.join(res.container_ids.mapped('name'))
        return res

    @api.multi
    def _get_usage(self):
        for pick in self:
            if not pick.location_id:
                pick.usage = pick.picking_type_id.default_location_src_id
            else:
                pick.usage = pick.location_id.usage

    @api.multi
    def action_cancel(self):
        for pick in self:
            if pick.temp:
                for move in pick.move_lines:
                    if move.state == "assigned":
                        move._do_unreserve()
                    move.state = "draft"
                    move.picking_id = False
                    move.product_id.product_tmpl_id._get_in_production_stock()
                pick.state = "cancel"

        return super(StockPicking, self).action_cancel()

    @api.multi
    def _get_containers(self):
        for picking in self:
            res = []
            for move in picking.move_lines:
                if move.container_id:
                    res.append(move.container_id.id)
            picking.container_ids = res


class StockMove(models.Model):

    _inherit = 'stock.move'

    partner_id = fields.Many2one('res.partner', 'Partner')
    container_id = fields.Many2one('stock.container', "Container")
    subtotal_price = fields.Float('Subtotal', compute='_calc_subtotal')
    partner_ref = fields.Char(related='purchase_line_id.order_id.partner_ref')

    @api.multi
    def _calc_subtotal(self):
        for move in self:
            move.subtotal_price = move.price_unit * move.product_uom_qty

    @api.multi
    def write(self, vals):
        for move in self:
            if 'product_uom_qty' in vals \
                    and self.purchase_line_id \
                    and self.picking_id \
                    and 'origin' not in vals\
                    and not move._context.get('accept_ready_qty'):
                if move.product_uom_qty > vals['product_uom_qty'] > 0:
                    move.copy({'picking_id': False, 'product_uom_qty': move.product_uom_qty - vals['product_uom_qty']})
                elif vals['product_uom_qty'] > move.product_uom_qty:
                    raise exceptions.Warning(_('Impossible to increase the quantity'))
                elif vals['product_uom_qty'] == 0:
                    raise exceptions.Warning(_('Impossible to decrease the quantity to 0'))
        res = super(StockMove, self).write(vals)
        for move in self:
            move.refresh()
            if move.picking_type_id.code == 'incoming':
                if vals.get('date_expected', False):
                    self.env['stock.reservation'].\
                        reassign_reservation_dates(move.product_id)
            if vals.get('container_id', False):
                container = self.env["stock.container"].\
                    browse(vals['container_id'])
                move.date_expected = container.date_expected
        return res

    @api.model
    def create(self, vals):
        res = super(StockMove, self).create(vals)
        if (vals.get('picking_type_id', False) and
                res.picking_type_id.code == 'incoming'):
            if 'date_expected' in vals.keys():
                self.env['stock.reservation'].\
                    reassign_reservation_dates(res.product_id)
        if not res.partner_id and res.picking_id.partner_id == \
                self.env.ref('purchase_picking.partner_multisupplier'):
            raise exceptions.Warning(
                _('Partner error'), _('Set the partner in the created moves'))
        return res

    @api.multi
    def unlink(self):
        products = self.env['product.template']
        for move in self:
            if move.purchase_line_id and move.state!='cancel':
                products += move.product_id.product_tmpl_id
        res = super(StockMove, self).unlink()
        if products:
            products._get_in_production_stock()
        return res


class StockReservation(models.Model):
    _inherit = 'stock.reservation'

    @api.model
    def reassign_reservation_dates(self, product_id):
        product_uom = product_id.uom_id
        reservations = self.search(
            [('product_id', '=', product_id.id),
             ('state', 'in', ['confirmed', 'partially_available'])])
        moves = self.env['stock.move'].search(
            [('product_id', '=', product_id.id),
             ('state', '=', 'draft'),
             ('picking_type_id.code', '=', u'incoming')],
            order='date_expected')
        reservation_index = 0

        reservation_used = 0
        for move in moves:
            qty_used = 0
            product_uom_qty = move.product_uom._compute_quantity(move.product_uom_qty, product_uom)
            while qty_used < product_uom_qty and reservation_index < len(reservations):
                reservation = reservations[reservation_index]
                reservation_qty = reservation.product_uom_qty - reservation.reserved_availability
                reservation_qty = move.product_uom._compute_quantity(reservation_qty, product_uom)
                if reservation_qty - reservation_used <= product_uom_qty - qty_used:
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

    @api.multi
    def reassign(self):
        res = super(StockReservation, self).reassign()
        for reservation in self:
            reservation.reassign_reservation_dates(reservation.product_id)
        return res
