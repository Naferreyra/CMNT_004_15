# Copyright 2019 Omar Castiñeira, Comunitea Servicios Tecnológicos S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Account custom',
    'version': '11.0.1.0.0',
    'category': 'account',
    'description': """
        Account customizations:
            -Relation between stock.move and account.invoice.line
            -Attach the picking report in invoice email.
    """,
    'author': 'Comunitea',
    'website': '',
    "depends": ['mail', 'account', 'stock', 'product_brand',
                'stock_account', 'sale_stock', 'account_payment_partner',
                'account_payment_mode', 'sale', 'purchase',
                'account_financial_risk', 'account_payment_order',
                'sale_margin_percentage', 'account_banking_sepa_direct_debit',
                'stock_reserve_sale', 'sales_team', 'partner_risk_insurance',
                'custom_partner', 'account_payment_return',
                'sale_advance_payment', 'account_banking_sepa_mail',
                'account_credit_control', 'stock_picking_invoice_link',
                'account_invoice_merge', 'customer_area',
                'res_currency_rate_force'],
    "data": ['views/account_view.xml',
             'views/partner_view.xml',
             'report/account_invoice_report_view.xml',
             'security/ir.model.access.csv',
             'views/stock_view.xml',
             'views/account_payment.xml',
             'views/purchase_view.xml',
             'views/account_analytic.xml',
             'report/sale_report_view.xml',
             'wizard/reconline_payment_with_statement_lines_wzd_view.xml',
             'wizard/reclassify_move_line_balance_wizard_view.xml',
             'wizard/wzd_remove_partners_from_payment_order_view.xml',
             'report/account_invoice_contact_report_view.xml',
             'views/account_bank_statement.xml',
             'wizard/statement_ignore.xml'
             ],
    "installable": True
}
