from odoo import models, _, api, fields, exceptions


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _compute_customizations(self):
        for picking in self:
            if picking.picking_type_id.code == 'outgoing':
                customization_ids = self.env['kitchen.customization']
                for move in picking.move_lines:
                    customization_line = move.customization_line
                    if customization_line:
                        customization_ids += customization_line.mapped('customization_id')
                picking.customization_ids = [(6, 0, customization_ids.ids)]
                picking.customization_count = len(set(customization_ids))

    customization_ids = fields.One2many('kitchen.customization', compute="_compute_customizations")

    customization_count = fields.Integer(compute='_compute_customizations', default=0)

    @api.onchange('not_sync')
    def onchange_not_sync(self):
        if self.customization_ids and self.customization_ids.filtered(
                lambda c: c.state not in ('cancel', 'done')):
            raise exceptions.UserError(_(
                'You cannot change this value because there are customizations in progress. Please, cancel the customization first'))

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
        for picking in self:
            if picking.picking_type_id.code == 'outgoing':
                customizations = picking.customization_ids.filtered(lambda c:c.state!='cancel')
                if customizations:
                    customizations_in_progress = customizations.filtered(lambda c1: c1.state in ('done', 'in_progress'))
                    if customizations_in_progress:
                        raise exceptions.UserError(
                            _("You cannot cancel this picking because there are customizations in progress"))
                    elif picking.sale_id:
                        return self.env['cancel.customizations.wiz'].create({
                            'picking_id': picking.id,
                            'origin_reference':
                                '%s,%s' % ('stock.picking', picking.id),
                            'continue_method': 'action_cancel',
                            'customizations_ids': [(6, 0, picking.customization_ids.ids)]
                        }).action_show()

        return super(StockPicking, self).action_cancel()


class StockMove(models.Model):
    _inherit = 'stock.move'

    customization_line = fields.One2many('kitchen.customization.line', related="sale_line_id.customization_line")
