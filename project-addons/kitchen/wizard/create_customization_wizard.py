from odoo import models, fields, api, exceptions, _

from odoo.exceptions import except_orm, UserError


class CustomizationLine(models.TransientModel):
    _name = 'customization.line'

    product_id = fields.Many2one('product.product', 'Product', readonly=1)
    qty = fields.Float('Selected quantity', default=0)
    product_qty = fields.Float('Quantity Available', readonly=1)
    wizard_id = fields.Many2one('customization.wizard', 'wizard')
    sale_line_id = fields.Many2one('sale.order.line')
    only_erase_logo = fields.Boolean()
    max_qty = fields.Float()


class CustomizationWizard(models.TransientModel):
    _name = 'customization.wizard'

    order_id = fields.Many2one('sale.order',
                               default=lambda self: self.env['sale.order'].browse(self.env.context.get('active_ids')))

    @api.model
    def _get_lines(self):
        wiz_lines = []
        customize_all = self.env['ir.config_parameter'].sudo().get_param('all.products.customize')
        for line in self.env['sale.order'].browse(self.env.context.get('active_ids')).order_line:
            new_line = {'product_id': line.product_id.id,
                        'qty': 0,
                        'sale_line_id': line.id}

            qty_done = sum(self.env['kitchen.customization.line'].search(
                [('sale_line_id', '=', line.id), ('state', '!=', 'cancel')]).mapped('product_qty'))
            if customize_all == 'False':
                moves = line.move_ids.filtered(lambda mv: 'cancel' != mv.state)
                qty = 0
                pack = self.env['mrp.bom']._bom_find(product=line.product_id)
                if pack and pack.type == 'phantom':
                    reserved_available = {}
                    for move in moves:
                        avail = move.product_id.uom_id._compute_quantity(
                            move.reserved_availability,
                            move.product_uom,
                            round=False)
                        pack_lines = pack.bom_line_ids.filtered(lambda l, m=move: l.product_id == m.product_id)
                        div_qty = 1
                        if pack_lines:
                            pack_lines_value = sum(pack_lines.mapped('product_qty'))
                            div_qty = pack_lines_value if pack_lines_value > 0 else 1
                        reserved_available[move.id] = avail // div_qty
                    if moves:
                        qty = min(reserved_available.values())
                else:
                    qty = sum(moves.mapped('product_uom_qty'))
                if qty > 0:
                    new_line.update({'product_qty': qty - qty_done,
                                     'max_qty': qty - qty_done})
            elif customize_all == 'True' and line.product_qty:
                new_line.update({'product_qty': line.product_qty - qty_done,
                                 'max_qty': line.product_qty - qty_done})
            if new_line.get('product_qty'):
                wiz_lines.append(new_line)
        return wiz_lines

    customization_line = fields.One2many('customization.line',
                                         'wizard_id', 'lines', default=_get_lines)
    type_ids = fields.Many2many('customization.type', required=1)

    erase_logo = fields.Boolean('Erase Logo')
    comments = fields.Text('Comments')
    add_all = fields.Boolean(string="Add All")
    notify_users = fields.Many2many('res.users')

    @api.onchange('add_all')
    def action_add_all(self):
        for line in self.customization_line:
            line.qty = line.product_qty if self.add_all else 0

    def action_create(self):
        lines = []
        customization = self.env['kitchen.customization'].create({'partner_id': self.order_id.partner_id.id,
                                                                  'type_ids': [(6, 0, self.type_ids.ids)],
                                                                  'erase_logo': self.erase_logo,
                                                                  'order_id': self.order_id.id,
                                                                  'commercial_id': self.order_id.user_id.id,
                                                                  'comments': self.comments,
                                                                  'notify_users': [(6, 0, self.notify_users.ids)]
                                                                  })
        for line in self.customization_line:
            qty = line.qty
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
                    'only_erase_logo': line.only_erase_logo
                }
                lines += self.env['kitchen.customization.line'].create(new_line)
        if lines:
            customization.action_confirm()
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
