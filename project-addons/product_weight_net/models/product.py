from odoo import api, fields, models
import odoo.addons.decimal_precision as dp


class ProductTemplate(models.Model):

    _inherit = 'product.template'

    weight_net = fields.Float('Net Weight', digits=dp.get_precision('Stock Weight'),
                              help="The net weight in Kg")


class ProductProduct(models.Model):

    _inherit = 'product.product'

    @api.multi
    def write(self, values):
        res = super().write(values)
        if values.get('weight', False) or values.get('weight_net', False) and self.used_in_bom_count:
            boms = self.env['mrp.bom'].search([('bom_line_ids.product_id', '=', self.id)])
            for product in boms.mapped('product_tmpl_id'):
                product.product_variant_ids.calculate_bom_weight()
        return res

    @api.multi
    def calculate_bom_weight(self):
        if self.bom_ids:
            weight_total = 0.0
            weight_net_total = 0.0
            for line in self.bom_ids[0].bom_line_ids:
                weight_total += line.product_id.weight * line.product_qty
                weight_net_total += line.product_id.weight_net * line.product_qty
            self.weight = weight_total or self.weight
            self.weight_net = weight_net_total or self.weight_net
