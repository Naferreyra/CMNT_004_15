from odoo import models, fields, _, exceptions, api
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    customization_ids = fields.One2many('kitchen.customization', 'order_id')

    def _compute_customization_count(self):
        for order in self:
            order.customization_count = len(order.customization_ids)

    customization_count = fields.Integer(compute='_compute_customization_count', default=0)

    def action_confirm(self):
        if any(e not in ('done', 'cancel') for e in self.customization_ids.mapped('state')):
            raise UserError(_("You can't transfer an order with pending customizations"))
        return super(SaleOrder, self).action_confirm()

    def action_view_customizations(self):
        if self.env.user.has_group('kitchen.group_kitchen'):
            action = self.env.ref('kitchen.action_show_customizations_kitchen').read()[0]
        else:
            action = self.env.ref('kitchen.action_show_customizations_commercials').read()[0]
        if len(self.customization_ids) > 0:
            action['domain'] = [('id', 'in', self.customization_ids.ids)]
            action['context'] = [('id', 'in', self.customization_ids.ids)]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    customization_line = fields.One2many('kitchen.customization.line', 'sale_line_id')
