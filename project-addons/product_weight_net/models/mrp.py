from odoo import api, fields, models


class MrpBom(models.Model):

    _inherit = 'mrp.bom'
    type = fields.Selection(default='phantom')

    @api.multi
    def write(self, values):
        res = super().write(values)
        for bom in self:
            bom.product_tmpl_id.product_variant_ids.calculate_bom_weight()
            bom.product_tmpl_id.recalculate_standard_price_2()
        return res

    @api.model
    def create(self, values):
        res = super().create(values)
        self.product_tmpl_id.product_variant_ids.calculate_bom_weight()
        self.product_tmpl_id.recalculate_standard_price_2()
        return res
