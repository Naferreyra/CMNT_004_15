##############################################################################
#
#    Copyright (C) 2015 Comunitea Servicios Tecnológicos All Rights Reserved
#    $Kiko Sanchez <kiko@comunitea.com>$
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
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import models, fields, api, exceptions
from datetime import date
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    shipping_balance = fields.Boolean('shipping_balance')
    amount_shipping_balance = fields.Float(related='partner_id.amount_shipping_balance')

    @api.constrains('state', 'amount_untaxed')
    def _check_amount_on_state(self):
        prepaid_discount_product_id=self.env.ref('prepaid_order_discount.prepaid_discount_product').id
        if self.amount_untaxed < 0 and \
                not self.order_line.filtered(lambda l: l.deposit or l.promotion_line or l.product_id.id==prepaid_discount_product_id):
            raise ValidationError("Total amount must be > 0")

    @api.multi
    def unlink(self):
        res = SaleOrder._action_unlink_shipping(self)
        if res:
            return super(SaleOrder, self).unlink()

    @api.multi
    def action_cancel(self, group=False):
        res = super(SaleOrder, self).action_cancel()
        if res:
            return SaleOrder._action_unlink_shipping(self)

    @api.multi
    def _action_unlink_shipping(self):
        for order in self:
            line2 = self.env['shipping.balance'].search([('sale_id', '=', order.id)])
            if line2:
                line2.unlink()
        return True


class SaleOrderLine(models.Model):

    _inherit = 'sale.order.line'

    @api.multi
    def unlink(self):
        res_id = self.mapped('order_id.id')

        res = super(SaleOrderLine, self).unlink()
        line2 = self.env['shipping.balance'].search([('sale_id', 'in', res_id)])
        if line2:
            line2.unlink()
        return True
