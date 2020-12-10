# Copyright 2019 Omar Castiñeira, Comunitea Servicios Tecnológicos S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'UBL EDI exchange to ES odoo',
    'version': '11.0.0.0.1',
    'author': 'Comunitea',
    'webbsite': 'https://www.comunitea.com',
    'description': """""",
    'depends': ['purchase_order_ubl','sale_display_stock'],
    'category': 'EDI',
    'data': ['views/purchase_view.xml','views/product_view.xml','views/sale_view.xml'],
    'auto_install': False,
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
