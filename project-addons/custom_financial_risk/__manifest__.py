# © 2019 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Financial risk customizations',
    'version': '11.0.1.0.0',
    'category': 'Accounting',
    'author': 'Comunitea',
    'website': 'www.comunitea.com',
    'license': 'AGPL-3',
    'depends': [
        'account_financial_risk',
        'sale_financial_risk',
        'order_invoice_policy'
    ],
    'data': [
        'views/account.xml',
        'views/res_partner.xml',
        'wizard/update_risk.xml'
    ],
    'installable': True,
}
