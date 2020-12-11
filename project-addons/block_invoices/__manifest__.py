# © 2019 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': "Block Invoices",
    'version': '11.0.1.0.0',
    'category': 'Accounting',
    'description': """Block sales and invoices for customers from due dates.""",
    'author': 'Alberto Luengo, Comunitea',
    'website': 'luengocabanillas.com, http://www.comunitea.com',
    "depends": ['sale', 'stock_account', 'custom_account', 'invoice_update_data'],
    "data": ['views/res_company_view.xml', 'views/res_partner_view.xml',
             'views/sale_view.xml', 'views/account_invoice_view.xml',
             'data/ir_cron.xml', 'data/parameters.xml', 'security/block_invoices.xml'],
    "installable": True
}
