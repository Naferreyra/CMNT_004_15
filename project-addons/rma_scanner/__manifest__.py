{
    'name': 'RMA Scanner',
    'version': '11.0.0.0.0',
    'summary': 'Scan the RMAs with a barcode scanner',
    'author': 'Visiotech',
    'license': 'AGPL-3',
    'depends': ['base', 'barcode_action', 'crm_claim', 'crm_claim_rma', 'crm_claim_rma_custom'],
    'data': ['views/claim_views.xml', 'views/vstock_location_views.xml',
             'security/ir.model.access.csv',],
    'installable': True,
}
