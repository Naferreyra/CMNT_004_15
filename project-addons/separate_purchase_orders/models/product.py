from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.multi
    def _get_in_production_stock(self):
        res = super(ProductTemplate, self)._get_in_production_stock()
        for product in self:
            if product.product_variant_ids:
                self.env.cr.execute(
                    """
                    SELECT pol.id FROM purchase_order_line pol
                    JOIN purchase_order po ON po.id = pol.order_id
                    WHERE pol.state = 'purchase_order' AND po.completed_purchase is False 
                    AND pol.company_id = %s AND pol.product_id in %s
                    """, (self.env.user.company_id.id, tuple(product.product_variant_ids.ids))
                )
                qty = self.env.cr.fetchall()
                if qty:
                    line_ids = [x[0] for x in qty]
                    lines = self.env['purchase.order.line'].browse(line_ids)
                    product.qty_in_production += sum(lines.mapped("production_qty"))
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