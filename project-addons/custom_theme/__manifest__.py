{
    "name": "custom theme",
    "description": "A custom theme",
    "version": "0.1",
    "category": "Theme/Backend",
    "data": [
        "views/assets.xml",
        "views/menu_icons.xml",
        "views/web.xml",
        "data/parameters.xml"
    ],
    "depends": [
        "web",
        "crm",
        "calendar",
        "sale",
        "queue_job",
        "purchase",
        "stock",
        "account",
        "base",
        "mrp",
    ],
    'qweb': [
        "static/xml/base.xml",
    ],
    "auto_install": False,
    "installable": True,
}
