{
    "name": "EDIFACT",
    "version": "11.0",
    "author": "Visiotech",
    "website": "",
    "sequence": 0,
    "certificate": "",
    "license": "",
    "depends": ["account"],
    "category": "Generic Modules/EDI",
    "description": """
    """,
    "data": [
        "views/res_partner_views.xml",
        "views/res_company_views.xml",
        "views/edi_views.xml",
        "views/account_invoice_views.xml",
        "data/parameters.xml",
        "data/edi_edifact_data.xml",
        "security/ir.model.access.csv"
    ],
    "auto_install": False,
    "installable": True,
    "application": True,
}
