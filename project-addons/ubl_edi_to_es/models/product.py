from odoo import models, fields

class ProductProduct(models.Model):
    _inherit = "product.product"

    virtual_stock_conservative_es = fields.Float('Qty Available ES')

class ProductTemplate(models.Model):
    _inherit = "product.template"

    virtual_stock_conservative_es = fields.Float('Qty Available ES')