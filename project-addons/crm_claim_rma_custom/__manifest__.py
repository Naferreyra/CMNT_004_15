##############################################################################
#
#    Copyright (C) 2015 Comunitea Servicios Tecnológicos All Rights Reserved
#    $Omar Castiñeira Saavedra <omar@comunitea.com>$
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
    'name': 'Crm Claim custom',
    'version': '11.0',
    'category': 'crm',
    'description': """
        Crm claim customizations:
    """,
    'author': 'Comunitea',
    'website': '',
    "depends": ['crm_claim_rma',
                'crm_claim_code',
                'account',
                'account_invoice_refund_link',
                'product_virtual_stock_conservative',
                'sale_display_stock',
                'crm_rma_advance_location',
                'custom_partner',
                # 'block_invoices',
                'product_brand',
                'mail',
                'picking_incidences'],
    "data": ['views/crm_claim_view.xml',
             'data/substate_data.xml',
             'security/ir.model.access.csv',
             'wizard/claim_make_picking_view.xml',
             'views/stock_view.xml',
             'wizard/claim_make_picking_from_picking_view.xml',
             'report/crm_claim_report_view.xml',
             'data/stage_data.xml',
             'wizard/equivalent_products_wizard_view.xml',
             'views/res_users_view.xml'],
    "installable": True
}
