from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    @api.multi
    def action_invoice_create(self):
        lines=self.env['sale.order.line']
        for order in self:
            promo_lines= order.mapped('order_line').filtered(lambda x: x.original_line_id_promo)
            for line in promo_lines:
                #For example in 4x3 promo, line.promo_qty_split is equals to 4
                #because this field show us the minimun qty of product for which the promo is applied
                qty_to_invoice=(line.original_line_id_promo.qty_invoiced +
                                line.original_line_id_promo.qty_to_invoice)//line.promo_qty_split - line.qty_invoiced
                line.qty_to_invoice=qty_to_invoice
                if qty_to_invoice==0:
                    lines+=line
        res= super(SaleOrder, self).action_invoice_create()
        for line in lines:
            if line.product_uom_qty!=line.qty_invoiced:
                line.qty_to_invoice=line.product_uom_qty-line.qty_invoiced
        return res


