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

from odoo import models, fields, api


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    area_id = fields.Many2one('res.partner.area', string='Area', store=True,
                              compute='_get_area_id')

    @api.depends('partner_shipping_id', 'partner_id')
    @api.multi
    def _get_area_id(self):
        for sale in self:
            if sale.partner_shipping_id.dropship:
                sale.area_id = sale.partner_id.area_id.id
            else:
                sale.area_id = sale.partner_shipping_id.area_id.id or sale.partner_id.area_id.id
