{
    "name": "Cron Stock Catalog",
    "description": "Cron to send the stock catalog every day to purchase department",
    "version": "0.1",
    "data": [
        "data/ir_cron.xml",
        "views/email_template.xml",
    ],
    "depends": ['stock',
    ],

    "auto_install": False,
    "installable": True,
}
