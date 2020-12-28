from odoo import models, fields, _, exceptions, api
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    customization_ids = fields.One2many('kitchen.customization', 'order_id')

    def _compute_customization_count(self):
        for order in self:
            order.customization_count = len(order.customization_ids)

    customization_count = fields.Integer(compute='_compute_customization_count', default=0)

    def _action_confirm(self):
        res = super(SaleOrder, self)._action_confirm()
        customizations = self.customization_ids.filtered(lambda p: p.state == 'draft')
        if customizations:
            pickings = self.picking_ids.filtered(lambda p: p.state != 'cancel')
            pickings.write({'not_sync':True})
            pickings.message_post(
                body=_('This picking has been created from an order with customized products'))
            for customization in customizations:
                customization.action_confirm()
        return res


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
