from odoo import models, fields

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    qty_available_es = fields.Float('Qty Avail. ES', related="product_id.virtual_stock_conservative_es",readonly=1)


