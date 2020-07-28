##############################################################################
#
#    Copyright (C) 2015 Comunitea Servicios Tecnológicos All Rights Reserved
#    $Omar Castiñeira Saavedra <omar@pcomunitea.com>$
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
    'name': "Partner custom",
    'version': '1.0',
    'category': 'Custom',
    'description': """Several little customizations in partners""",
    'author': 'Comunitea Servicios Tecnológicos',
    'website': 'www.comunitea.com',
    "depends": ['base', 'sale', 'l10n_es_partner', 'account',
                'base_partner_sequence', 'stock', 'account_credit_control',
                'purchase', 'prospective_customer', 'account_due_list',
                'customer_lost', 'sale_margin_percentage', 'contacts',
                'crm_phone_validation', 'commercial_rules'],
    "data": ["views/partner_view.xml",
             "views/sale_view.xml",
             "security/ir.model.access.csv",
             "data/custom_partner_data.xml",
             "security/groups.xml",
             "data/parameters.xml"],
    "installable": True
}
