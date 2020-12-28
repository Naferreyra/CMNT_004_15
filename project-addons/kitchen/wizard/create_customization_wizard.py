from odoo import models, fields, api, exceptions, _

from odoo.exceptions import except_orm, UserError


class CustomizationLine(models.TransientModel):
    _name = 'customization.line'

    product_id = fields.Many2one('product.product', 'Product', readonly=1)
    qty = fields.Float('Selected quantity', default=0)
    product_qty = fields.Float('Quantity Available', readonly=1)
    wizard_id = fields.Many2one('customization.wizard', 'wizard')
    sale_line_id = fields.Many2one('sale.order.line')
    erase_logo = fields.Boolean()
    max_qty = fields.Float()
    qty_reserved = fields.Float()
    type_ids = fields.Many2many('customization.type', required=1)


class CustomizationWizard(models.TransientModel):
    _name = 'customization.wizard'

    order_id = fields.Many2one('sale.order',
                               default=lambda self: self.env['sale.order'].browse(self.env.context.get('active_ids')))

    @api.model
    def _get_lines(self):
        wiz_lines = []
        for line in self.env['sale.order'].browse(self.env.context.get('active_ids')).order_line.filtered(
                lambda l: not l.deposit and l.product_id.categ_id.with_context(
                    lang='es_ES').name != 'Portes' and l.price_unit >= 0):
            new_line = {'product_id': line.product_id.id,
                        'qty': line.product_qty,
                        'sale_line_id': line.id,
                        'type_ids': None}

            qty_done = sum(self.env['kitchen.customization.line'].search(
                [('sale_line_id', '=', line.id), ('state', '!=', 'cancel')]).mapped('product_qty'))

            if line.product_qty:
                new_line.update({'product_qty': line.product_qty - qty_done,
                                 'max_qty': line.product_qty - qty_done})
            if new_line.get('product_qty'):
                wiz_lines.append(new_line)
        return wiz_lines

    customization_line = fields.One2many('customization.line',
                                         'wizard_id', 'lines', default=_get_lines)
    type_ids = fields.Many2many('customization.type', required=1)

    comments = fields.Text('Comments')

    notify_users = fields.Many2many('res.users', default=lambda self: [
        (6, 0, [self.env['sale.order'].browse(self.env.context.get('active_ids')).user_id.id])])

    @api.onchange('add_all')
    def action_add_all(self):
        for line in self.customization_line:
            line.qty = line.product_qty if self.add_all else 0

    def action_create(self):
        lines = []
        customization = self.env['kitchen.customization'].sudo().create({'partner_id': self.order_id.partner_id.id,
                                                                  'order_id': self.order_id.id,
                                                                  'commercial_id': self.order_id.user_id.id,
                                                                  'comments': self.comments,
                                                                  'notify_users': [(6, 0, self.notify_users.ids)]
                                                                  })
        for line in self.customization_line:
            qty = line.qty
            if not line.type_ids:
                raise UserError(_(
                    "You can't create a customization without a customization type: %s") % line.sale_line_id.product_id.default_code)
            if qty < 0:
                raise UserError(_(
                    "You can't create a customization with a quantity of less than zero of this product: %s") % line.sale_line_id.product_id.default_code)
            elif line.max_qty < qty:
                raise UserError(_(
                    "You can't create a customization with a bigger quantity of the product than what appears in the order: %s") % line.sale_line_id.product_id.default_code)
            elif qty > 0:
                new_line = {
                    'product_id': line.sale_line_id.product_id.id,
                    'product_qty': line.qty,
                    'customization_id': customization.id,
                    'sale_line_id': line.sale_line_id.id,
                    'erase_logo': line.erase_logo,
                    'type_ids': [(6, 0, line.type_ids.ids)]
                }
                lines += self.env['kitchen.customization.line'].create(new_line)
        if lines:
            return {
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': self.env.ref('kitchen.kitchen_customization_form').id,
                'res_model': 'kitchen.customization',
                'res_id': customization.id,
                'type': 'ir.actions.act_window',
            }
        else:
            raise UserError(_("You cannot create an empty customization"))
