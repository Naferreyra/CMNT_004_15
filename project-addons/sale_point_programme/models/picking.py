##############################################################################
#
#    Copyright (C) 2014 Pexego Sistemas Informáticos All Rights Reserved
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

from odoo import models, api, fields


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    def create_negative_points_programme_bag(self):
        obj_bag = self.env['res.partner.point.programme.bag']
        bag_ids = obj_bag.search([('order_id', '=', self.sale_id.id)])
        if bag_ids:
            rules = bag_ids.mapped('point_rule_id')
            rules_with_points, brands, products, categories = self.sale_id.compute_points_programme_bag(self.move_lines,rules,"move")
            for rule,points in rules_with_points.items():
                modality_type = rule.modality
                if ((rule.product_brand_id.id in brands) | (rule.product_id.id in products) |
                    (rule.category_id.id in categories)) and modality_type == 'point' and points:
                    obj_bag.create({'name': rule.name,
                                    'point_rule_id': rule.id,
                                    'order_id': self.sale_id.id,
                                    'points': -points,
                                    'partner_id': self.sale_id.partner_id.id})

    @api.multi
    def action_cancel(self):
        res = super(StockPicking, self).action_cancel()
        for picking in self:
            if picking.sale_id:
                picking.create_negative_points_programme_bag()
        return res

    @api.multi
    def action_done(self):
        res = super(StockPicking, self).action_done()
        for picking in self:
            if picking.sale_id and picking.picking_type_id.code == "incoming":
                picking.create_negative_points_programme_bag()
        return res


