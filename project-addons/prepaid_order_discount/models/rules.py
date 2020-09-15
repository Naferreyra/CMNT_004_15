from odoo import models


class PromotionsRulesActions(models.Model):
    _inherit = 'promos.rules.actions'


    def action_cart_disc_perc(self, order):
        """
        Discount % on Sub Total (without prepaid discount)
        """
        res = super(PromotionsRulesActions, self).action_cart_disc_perc(order)

        prepaid_discount_product_id = self.env.ref('prepaid_order_discount.prepaid_discount_product').id
        exist_prepaid_discount_line = order.order_line. \
            filtered(lambda l: l.product_id.id == prepaid_discount_product_id)
        if exist_prepaid_discount_line:
            order_lines_sorted_by_id = order.order_line.sorted(key=lambda l: l.id)
            last_product_order = order_lines_sorted_by_id[-1]
            last_product_order.price_unit += exist_prepaid_discount_line.price_subtotal*eval(self.arguments) /100
        return res

