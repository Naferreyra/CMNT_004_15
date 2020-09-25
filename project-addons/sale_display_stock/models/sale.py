##############################################################################
#
#    Copyright (C) 2004-2014 Pexego Sistemas Informáticos All Rights Reserved
#    $Marta Vázquez Rodríguez$ <marta@pexego.es>
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
import odoo.addons.decimal_precision as dp


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    qty_available = fields.\
        Float('Qty available', readonly=True, compute="_compute_qty_available",
              digits=dp.get_precision('Product Unit of Measure'))

    incoming_qty = fields.\
        Float('Incoming qty.', readonly=True, compute='_get_incoming_qty',
              digits=dp.get_precision('Product Unit of Measure'))

    @api.multi
    @api.depends('product_id')
    def _compute_qty_available(self):
        for line in self:
            line.qty_available = line.product_id.virtual_stock_conservative - line.product_id.qty_available_input_loc

    @api.multi
    def _get_incoming_qty(self):
        for sol in self:
            incoming_qty = 0
            if sol.product_id:
                product = sol.product_id
                incoming_qty = product.incoming_qty + \
                    product.qty_available_input_loc
            sol.incoming_qty = incoming_qty


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    @api.returns('self', lambda value: value.id)
    def message_post(self, **kwargs):
        context = dict(self.env.context)
        context.pop('mail_post_autofollow', False)
        self = self.with_context(context)
        return super(SaleOrder, self).message_post(**kwargs)
