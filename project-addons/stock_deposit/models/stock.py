##############################################################################
#
#    Author: Santi Argüeso
#    Copyright 2014 Pexego Sistemas Informáticos S.L.
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

from odoo import models, api, fields
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import time
from datetime import datetime, timedelta


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def _action_done(self):
        res = super(StockMove, self)._action_done()
        deposit_obj = self.env['stock.deposit']
        for move in self:
            if move.sale_line_id.deposit and \
                    move.picking_type_id.code == "outgoing":
                formatted_date = datetime.strptime(time.strftime('%Y-%m-%d'),
                                                   "%Y-%m-%d")
                return_date = datetime.\
                    strftime(formatted_date + timedelta(days=15), "%Y-%m-%d")
                values = {
                    'move_id': move.id,
                    'delivery_date':
                    time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'return_date':
                    move.sale_line_id.deposit_date or
                    return_date,
                    'user_id':
                    move.sale_line_id.order_id.user_id.id,
                    'state': 'draft'
                }
                deposit_obj.create(values)
        return res


class ProcurementRule(models.Model):
    _inherit = 'procurement.rule'

    def _get_stock_move_values(self, product_id, product_qty, product_uom,
                               location_id, name, origin, values, group_id):
        vals = super(ProcurementRule, self)._get_stock_move_values(
            product_id, product_qty, product_uom,
            location_id, name, origin, values, group_id)
        if self.env['sale.order.line'].browse(vals['sale_line_id']).deposit:
            picking_type_id = self.env['stock.picking.type'].\
                search([('name', '=', u'Depósitos')])
            vals['location_dest_id'] = self.env['sale.order.line'].\
                browse(vals['sale_line_id']).order_id.partner_id.\
                commercial_partner_id.property_stock_deposit.id
            vals['picking_type_id'] = picking_type_id.id

        return vals


class StockLotacion(models.Model):

    _inherit = 'stock.location'

    deposit = fields.Boolean("Deposit", default=False)

