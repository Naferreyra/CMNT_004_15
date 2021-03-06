# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Product Pricelist Custom",
    "version": "11.0.0.0.0",
    "author": "Nadia Ferreyra",
    "category": "Product",
    "description": """
    Product Pricelist Customizations
    Add margins and relations on product pricelist
""",
    "depends": ["base", "product", "sale_customer_discount"],
    "data": [
        "views/product_view.xml", "security/product_pricelist_custom.xml"
    ],
    "demo": [],
    'auto_install': False,
    "installable": True,
    'images': [],
}
