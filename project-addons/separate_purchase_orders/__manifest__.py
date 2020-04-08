
{
    'name': "Separate purchase orders",
    'version': '11.0',
    'category': 'purchase',
    'description': """This module allows separate purchase orders in other smaller orders""",
    'author': 'Visiotech',
    'website': 'www.visiotechsecurity.es',
    "depends": ['purchase',
                'stock',
                'account'],
    "data": ['views/purchase_view.xml',
             'wizard/separate_orders_wizard.xml'],
    "installable": True
}
