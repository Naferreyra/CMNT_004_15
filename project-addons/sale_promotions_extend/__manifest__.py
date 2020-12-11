# © 2019 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Promotions Extend",
    "version": "11.0.1.0.0",
    "author": "Pexego",
    'website': 'www.pexego.es',
    "category": "Generic Modules/Sales & Purchases",
    "description": """
Promotions extend
========================================
Features:
1. Lets you apply discounts by product tags.
""",
    "depends": ["base",
                "commercial_rules",
                "equivalent_products",
                "stock_reserve_sale",
                "product_brand",
                "sale_product_customize",
                "sale_point_programme"],
    "data": [
        "views/sale_view.xml",
        "views/rule.xml",
        "views/product_view.xml",
        'security/ir.model.access.csv'
    ],
    "demo": [],
    'auto_install': False,
    "installable": True,
    'images': [],
}
