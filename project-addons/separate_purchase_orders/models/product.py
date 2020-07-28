from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.multi
    def _get_in_production_stock(self):
        res= super(ProductTemplate, self)._get_in_production_stock()
        for product in self:
            if product.product_variant_ids:
                order_lines = self.env["purchase.order.line"].search([('product_id', 'in', product.product_variant_ids.ids),
                                                       ('order_id.state', '=', 'purchase_order'),('order_id.completed_purchase','=',False)])
                qty = 0.0
                for order_line in order_lines:
                    qty += order_line.production_qty
                product.qty_in_production += qty
        return res

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def _split_purchase_count(self):
        domain = [
            ('order_id.state', '=', 'purchase_order'),
            ('product_id', 'in', self.mapped('id')),
        ]
        PurchaseOrderLines = self.env['purchase.order.line'].search(domain)
        for product in self:
            product.split_purchase_count = len(
                PurchaseOrderLines.filtered(lambda r: r.product_id == product).mapped('order_id'))

    split_purchase_count = fields.Integer(compute='_split_purchase_count')