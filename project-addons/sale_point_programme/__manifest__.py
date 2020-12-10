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

{
    'name': "Sale points programme",
    'version': '1.0',
    'category': 'sale',
    'description': """Allows to include rules to price customer with point
for fidelization programmes""",
    'author': 'Pexego Sistemas Informáticos',
    'website': 'www.pexego.es',
    "depends": ['sale',
                'sales_team',
                'base',
                'product',
                'crm_claim_rma_custom'],
    "data": ['views/partner_point_bag_view.xml',
             'views/sale_point_rule_view.xml',
             'views/sale_participations_cron.xml',
             'views/template_participations.xml',
             'views/partner_view.xml',
             'security/ir.model.access.csv',
             'data/cron.xml'],
    "installable": True
}
