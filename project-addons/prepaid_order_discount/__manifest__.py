
{
    'name': 'Discount prepaid order',
    'version': '1.0',
    'category': 'Custom',
    'description': """
        Order Discount when it's prepaid and margin is between specific values 
    """,
    'author': 'Nadia Ferreyra',
    'website': '',
    'depends': ['base',
                'sale',
                'product',
                'sale_promotions_extend',
                'commercial_rules',
                'flask_middleware_connector'
                ],
    'data': ['data/product_data.xml',
             'data/parameters.xml',
             'views/sale_order_view.xml',
             'views/account_view.xml'
             ],
    'installable': True
}

