from odoo import models, fields, api, exceptions, _

from odoo.exceptions import except_orm, UserError


class OrderLineDetails(models.TransientModel):
    _name = 'order.line.details'

    product_id = fields.Many2one('product.product', 'Product')
    qty = fields.Float('Quantity', default=0)
    production_qty = fields.Float('Production Quantity')
    wizard_id = fields.Many2one('separate.orders.wizard', 'wizard')
    purchase_line_id = fields.Many2one('purchase.order.line', 'Purchase order line')


class SeparateOrdersWizard(models.TransientModel):
    _name = 'separate.orders.wizard'

    @api.model
    def _get_lines(self):
        wiz_lines = []
        order = self.env.context.get('active_ids')
        for line in self.env['purchase.order'].browse(order).order_line:
            if line.production_qty > 0:
                wiz_lines.append({'product_id': line.product_id.id,
                                  'production_qty': line.production_qty,
                                  'purchase_line_id': line.id,
                                  'qty': 0})
        return wiz_lines

    order_line_details = fields.One2many('order.line.details',
                                         'wizard_id', 'lines', default=_get_lines)

    date_planned = fields.Datetime(string='Date Planned', required=1)
    add_all = fields.Boolean(string="Add All")

    @api.onchange('add_all')
    def action_add_all(self):
        for line in self.order_line_details:
            line.qty = line.production_qty if self.add_all else 0

    def action_separate_orders(self):
        lines = []
        order = self.env['purchase.order']
        original_order = self.env['purchase.order']
        for line in self.order_line_details:
            qty = line.qty
            if qty < 0 or line.purchase_line_id.production_qty - qty < 0:
                raise UserError(_("You cannot create a order with more quantity than"
                                  " production quantity of this product %s") % line.purchase_line_id.product_id.default_code)
            elif qty > 0:
                if not original_order:
                    original_order = line.purchase_line_id.order_id
                    order = order.create({'partner_id': original_order.partner_id.id,
                                          'partner_ref': original_order.partner_ref,
                                          'currency_id': original_order.currency_id.id,
                                          'parent_id': original_order.id,
                                          'date_planned': self.date_planned,
                                          'remark': original_order.remark
                                          })

                new_line = {
                    'product_id': line.purchase_line_id.product_id.id,
                    'price_unit': line.purchase_line_id.price_unit,
                    'product_qty': line.qty,
                    'discount': line.purchase_line_id.discount,
                    'product_uom': line.purchase_line_id.product_uom.id,
                    'order_id': order.id,
                    'name': line.purchase_line_id.name,
                    'taxes_id': [(6, 0, [x.id for x in line.purchase_line_id.taxes_id])],
                    'parent_id': line.purchase_line_id.id,
                    'date_planned': self.date_planned,
                }
                lines += self.env['purchase.order.line'].create(new_line)
        if lines:

            return {
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': self.env.ref('purchase.purchase_order_form').id,
                'res_model': 'purchase.order',
                'res_id': order.id,
                'type': 'ir.actions.act_window',
            }

        else:
            raise UserError(_("You cannot create an empty order"))
