from odoo import _, api, fields, models


class CancelCustomizationsWiz(models.TransientModel):
    _name = 'cancel.customizations.wiz'

    picking_id = fields.Many2one("sale.order", readonly=True, string='Sale')
    origin_reference = fields.Reference(
        lambda self: [
            (m.model, m.name) for m in self.env['ir.model'].search([])],
        string='Object')
    continue_method = fields.Char()
    customizations_ids = fields.Many2many('kitchen.customization')

    @api.multi
    def action_show(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cancel Customizations'),
            'res_model': self._name,
            'res_id': self.id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    @api.multi
    def button_continue(self):
        self.ensure_one()
        self.customizations_ids.action_cancel()
        return getattr(self.origin_reference, self.continue_method)()
