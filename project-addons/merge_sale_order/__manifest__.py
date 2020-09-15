{
    'name': 'Merge Sale Order',
    'category': 'Sales',
    'description': 'This module will merge sale order.',
    'version': '11.0',
    'author': 'Visiotech',
    'website': 'www.visiotechsecurity.es',

    'depends': [
        'sale_management',
        'sale',
        'reserve_without_save_sale',
        'prepaid_order_discount'        
    ],

    'data': [
        'wizard/merge_sale_order_wizard_view.xml',
    ],

    'installable': True,

}
