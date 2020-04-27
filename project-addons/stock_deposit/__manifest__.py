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
    'name': 'Stock deposit',
    'version': '11.0',
    'category': 'product',
    'description': """Manage deposit of goods in a customer location""",
    'author': 'Pexego Sistemas Informáticos',
    'website': 'www.pexego.es',
    'depends': ['base', 'sales_team', 'sale_stock', 'sale', 'order_invoice_policy'],
    'data': ['wizard/stock_invoice_deposit.xml', 'wizard/stock_sale_deposit.xml',
              'views/stock_data.xml', 'views/stock_deposit.xml', 'views/res_partner_view.xml',
              'security/ir.model.access.csv', 'views/sale_view.xml',
              'data/stock_deposit_data.xml'],
    'installable': True
}
