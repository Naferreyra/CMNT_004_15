# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Update invoice data',
    'version': '11.0.1.0.0',
    'category': '',
    'description': "Allow to update invoice data: payment mode, partner mandate... ",
    'author': 'Nadia Ferreyra',
    'website': '',
    "depends": ['account', 'payment', 'account_payment_partner', 'account_banking_mandate'],
    "data": ['wizard/invoice_update_payment_data_view.xml',
             'data/parameters.xml'],
    "installable": True
}
