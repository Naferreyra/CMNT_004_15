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
    'name': "Product Ship Balance",
    'version': '11.0',
    'category': 'product',
    'description': """Adds shipping balance""",
    'author': 'Comunitea Servicios Tecnologicos',
    'website': 'www.comunitea.com',
    "depends": ["base", "product", "mrp_repair", "sale", "account",
                "stock_reserve_sale", "sale_customer_discount", "prepaid_order_discount"],

    "data": ["views/shipping_balance_view.xml",
              "wizard/shipping_balance_wizard.xml",
              "views/partner_view.xml",
              "views/sale_order.xml",
              "views/product_view.xml",
              "security/ir.model.access.csv"
             ],
    "installable": True
}
