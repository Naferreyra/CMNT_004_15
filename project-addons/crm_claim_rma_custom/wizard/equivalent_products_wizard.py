from odoo import models, fields, api


class EquivalentProductsWizard(models.TransientModel):

    _inherit = 'equivalent.products.wizard'

    kitchen_stock = fields.Float("Kitchen Stock", readonly=True)
    virtual_stock_conservative = fields.Float("Available Stock", readonly=True)

    def default_get(self, fields):
        res = super(EquivalentProductsWizard, self).default_get(fields)
        if self.env.context.get('claim_line'):
            claim_line_id = self.env.get('claim.line').browse(self.env.context['claim_line'])
            res['kitchen_stock'] = claim_line_id.product_id.qty_available_wo_wh
            res['virtual_stock_conservative'] = claim_line_id.product_id.virtual_stock_conservative
        return res

    @api.onchange('product_id')
    def onchange_product(self):
        # super(EquivalentProductsWizard, self).onchange_product()
        self.kitchen_stock = self.product_id.qty_available_wo_wh
        self.virtual_stock_conservative = self.product_id.virtual_stock_conservative
        self.virtual_stock = self.product_id.virtual_available
        self.real_stock = self.product_id.qty_available
        self.product_tag_ids = self.product_id.tag_ids
