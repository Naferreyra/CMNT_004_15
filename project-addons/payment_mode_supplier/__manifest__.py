{
    'name': "Payment Mode Supplier",
    'version': '1.0',
    'category': 'Custom',
    'description': """Several little customizations in partners and purchase orders""",
    'author': 'Alberto Cañal Liberal',
    "depends": ['purchase'],
    "data": ["views/partner_view.xml",
             "views/purchase_view.xml",
             "views/payment_mode_supplier_view.xml",
             "security/ir.model.access.csv"
             ],
    "installable": True
}