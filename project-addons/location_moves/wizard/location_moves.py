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


from odoo import models, fields, api


class LocationMoves(models.TransientModel):

    _name = "location.moves"

    product_id = fields.Many2one('product.product', 'Product', required=True)
    qty = fields.Float('Qty', required=True)
    check_qty = fields.Boolean('Check Qty',
                               default=lambda self: self.env.context.
                               get('manual', False))

    move_type = fields.Selection(
        [('beach_stock', 'Beach -> Stock'),
         ('beach_kitchen', 'Beach -> Kitchen'),
         ('beach_pantry', 'Beach -> Pantry'),
         ('stock_kitchen', 'Stock -> Kitchen'),
         ('stock_pantry', 'Stock -> Pantry'),
         ('pantry_kitchen', 'Pantry -> Kitchen'),
         ('kitchen_cooked', 'Kitchen -> Cooked'),
         ('kitchen_nursing', 'Kitchen -> Nursing'),
         ('stock_nursing', 'Stock -> Nursing'),
         ('nursing_damaged', 'Nursing -> Damaged'),
         ('nursing_cooked', 'Nursing -> Cooked'),
         ('quality_cooked', 'Quality -> Cooked'),
         ('cooked_quality', 'Cooked -> Quality'),
         ('cooked_damaged', 'Cooked -> Damaged'),
         ('marketing_stock', 'Marketing -> Stock'),
         ('marketing_product', 'Marketing -> Product'),
         ('stock_marketing', 'Stock -> Marketing'),
         ('product_stock', 'Product -> Stock'),
         ('stock_product', 'Stock -> Product'),
         ('development_stock', 'Development -> Stock'),
         ('stock_development', 'Stock -> Development'),
         ('sat_stock', 'SAT -> Stock'),
         ('stock_sat', 'Stock -> SAT'),
         ],
        'Move type', required=True)

    @api.one
    def create_moves(self):
        loc_obj = self.env['stock.location']
        types = {
            'beach_stock': loc_obj.move_beach_stock,
            'beach_kitchen': loc_obj.move_beach_kitchen,
            'beach_pantry': loc_obj.move_beach_pantry,
            'stock_kitchen': loc_obj.move_stock_kitchen,
            'stock_pantry': loc_obj.move_stock_pantry,
            'pantry_kitchen': loc_obj.move_pantry_kitchen,
            'kitchen_cooked': loc_obj.move_kitchen_cooked,
            'kitchen_nursing': loc_obj.move_kitchen_nursing,
            'stock_nursing': loc_obj.move_stock_nursing,
            'nursing_damaged': loc_obj.move_nursing_damaged,
            'nursing_cooked': loc_obj.move_nursing_cooked,
            'quality_cooked': loc_obj.move_quality_cooked,
            'cooked_damaged': loc_obj.move_cooked_damaged,
            'marketing_stock': loc_obj.move_marketing_stock,
            'stock_marketing': loc_obj.move_stock_marketing,
            'product_stock': loc_obj.move_product_stock,
            'stock_product': loc_obj.move_stock_product,
            'development_stock': loc_obj.move_development_stock,
            'stock_development': loc_obj.move_stock_development,
            'sat_stock': loc_obj.move_sat_stock,
            'stock_sat': loc_obj.move_stock_sat,
            'cooked_quality': loc_obj.move_cooked_quality,
            'marketing_product': loc_obj.move_marketing_product
        }
        types[self.move_type](self.product_id.id, self.qty, self.check_qty)
        return True
