from odoo import _, api, fields, models


class MaxWeightAdviseWiz(models.TransientModel):
    _name = 'max.weight.advise.wiz'

    sale_id = fields.Many2one("sale.order", readonly=True, string='Sale')
    origin_reference = fields.Reference(
        lambda self: [
            (m.model, m.name) for m in self.env['ir.model'].search([])],
        string='Object')
    continue_method = fields.Char()
    message = fields.Char(readonly=True)

    @api.multi
    def action_show(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Max Weight Advise'),
            'res_model': self._name,
            'res_id': self.id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    @api.multi
    def button_continue(self):
        self.ensure_one()
        return getattr(self.origin_reference.with_context(
            bypass_canary_max_weight=True), self.continue_method)()
