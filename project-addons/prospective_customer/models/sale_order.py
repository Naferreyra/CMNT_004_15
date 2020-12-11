from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_confirm(self):
        if not self.env.context.get('bypass_risk', False) or self.env.context.get('force_check', False):
            for order in self:
                if order.partner_id.prospective:
                    order.partner_id.write({'active': True, 'prospective': False})
        res = super().action_confirm()
        return res
