{
    'name': "Separate purchase orders",
    'version': '11.0',
    'category': 'purchase',
    'description': """This module allows separate purchase orders in other smaller orders""",
    'author': 'Visiotech',
    'website': 'www.visiotechsecurity.es',
    "depends": ['purchase',
                'stock',
                'account',
                'sale_display_stock',
                'custom_account',
                'purchase_picking'],
    "data": ['wizard/separate_orders_wizard.xml',
             'views/purchase_view.xml',
             "data/sequence.xml"
             ],
    "installable": True
}
