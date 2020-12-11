from odoo import models, fields


class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    compute_price = fields.Selection(index=False)
