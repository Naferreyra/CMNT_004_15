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

{
    'name': "Purchase picking",
    'version': '11.0',
    'category': 'purchase',
    'description': """When a purchase order is confirmed, creates the associated moves without picking.""",
    'author': 'Pexego Sistemas Informáticos',
    'website': 'www.pexego.es',
    "depends": ['base',
                'purchase_discount',
                'stock',
                'product',
                'stock_reserve'],
    "data": ['wizard/create_picking_move_view.xml',
             'views/purchase_view.xml',
             'data/res_partner_data.xml',
             'views/stock_view.xml',
             'security/ir.model.access.csv',
             'security/purchase_picking_security.xml',
             'wizard/assign_container_view.xml',
             'wizard/cancel_moves_view.xml'],
    "installable": True
}
