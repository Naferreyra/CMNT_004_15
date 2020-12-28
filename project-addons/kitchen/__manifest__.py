{
    'name': "Kitchen customizations",
    'version': '11.0.1.0.0',
    'category': 'Integration',
    'description': """This module allows you to create and view product customizations""",
    'author': 'Visiotech',
    'website': 'www.visiotechsecurity.com',
    "depends": ['base','sale','sale_stock'],
    "data": [
        'data/kitchen_group.xml','wizard/customization_wizard.xml', 'views/kitchen_customization.xml', 'data/sequence.xml',
        'data/emails_kitchen.xml','wizard/create_customization_wizard.xml',
        'views/sale_order.xml','security/ir.model.access.csv','views/customization_type_view.xml'],
    "installable": True
}
