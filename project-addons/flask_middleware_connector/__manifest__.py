# © 2019 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Flask middleware connector',
    'version': '11.0.1.0.0',
    'category': 'Connector',
    'description': '''Connect to Visiotech flask middleware using Odoo connector''',
    'author': 'Comunitea',
    'website': 'www.comunitea.com',
    'depends': ['base', 'product', 'connector', 'queue_job', 'stock',
                'custom_partner', 'crm_claim_rma_custom',
                'product_virtual_stock_conservative', 'mrp', 'rappel', 'product_pricelist_custom',
                'custom_report_link', 'custom_account'],
    'data': [
        'views/middleware_view.xml', 'views/res_users.xml',
        'views/product_view.xml', 'views/product_brand.xml',
        'views/claim_line_view.xml','views/res_partner_view.xml', 'wizard/middleware_wizard_view.xml',
        'security/ir.model.access.csv', 'data/parameters.xml'
    ],
    'installable': True
}
