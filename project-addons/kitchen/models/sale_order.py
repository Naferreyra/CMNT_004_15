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
            pickings.write({'not_sync': True})
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

    @api.multi
    def action_cancel(self):
        for sale in self:
            customizations = sale.customization_ids.filtered(lambda c: c.state != 'cancel')
            if customizations:
                if sale.state == 'reserve':
                    customizations.action_cancel()
                else:
                    customizations_in_progress = customizations.filtered(lambda c: c.state in ('done', 'in_progress'))
                    if customizations_in_progress:
                        raise exceptions.UserError(
                            _("You cannot cancel this order because there are customizations in progress"))
                    else:
                        customizations.action_cancel()

        return super(SaleOrder, self).action_cancel()

    def action_confirm(self):
        if self.customization_ids and all([x.state == 'cancel' for x in self.customization_ids]):
            return self.env['retrieve.customizations.wiz'].create({
                'sale_id': self.id,
                'origin_reference':
                    '%s,%s' % ('sale.order', self.id),
                'continue_method': 'action_confirm',
                'customizations_ids': [(6, 0, self.customization_ids.ids)]
            }).action_show()
        return super(SaleOrder, self).action_confirm()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    customization_line = fields.One2many('kitchen.customization.line', 'sale_line_id')
