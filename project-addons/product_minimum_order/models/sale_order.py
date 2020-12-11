from odoo import models, fields, api, exceptions, _


class SaleOrderLine(models.Model):

    _inherit = 'sale.order.line'

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):

        res = super(SaleOrderLine, self).product_id_change()

        if self.product_id and self.product_uom_qty % self.product_id.sale_in_groups_of != 0:
            self.product_uom_qty = self.product_id.sale_in_groups_of

        return res

    @api.onchange('product_uom', 'product_uom_qty')
    def product_uom_change(self):

        res = super(SaleOrderLine, self).product_uom_change()

        if self.product_id:
            if self.product_uom_qty % self.product_id.sale_in_groups_of != 0:
                raise exceptions.Warning(
                    _("The product {0} can only be sold in groups of {1}")
                    .format(self.product_id.name, self.product_id.sale_in_groups_of))

        return res


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    @api.multi
    def action_confirm(self):
        if not self.env.context.get('bypass_risk', False) or self.env.context.get('force_check', False):
            for sale in self:
                for line in sale.order_line:
                    if line.product_id and line.product_id.sale_in_groups_of != 0.0:
                        if line.product_uom_qty % line.product_id.sale_in_groups_of != 0:
                            raise exceptions.Warning(
                                _("The product {0} can only be sold in groups of {1}")
                                .format(line.product_id.name, line.product_id.sale_in_groups_of))

        res = super(SaleOrder, self).action_confirm()

        return res
