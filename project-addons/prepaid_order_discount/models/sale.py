# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, fields, exceptions, _


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    prepaid_option = fields.Boolean("Prepaid option")

    @api.multi
    def action_confirm(self):
        for sale in self:
            message = ''
            if sale.prepaid_option:
                prepaid_discount_product_id = self.env.ref('prepaid_order_discount.prepaid_discount_product').id
                exist_prepaid_discount_line = sale.order_line.\
                    filtered(lambda l: l.product_id.id == prepaid_discount_product_id)
                if not exist_prepaid_discount_line:
                    message = _("It's an order with prepaid option. "
                                "Please, calculate the discount if partner has prepaid or cancel the prepaid option.")
                else:
                    last_product_order = sale.order_line.sorted(key=lambda l: l.sequence)[-1]
                    if exist_prepaid_discount_line.id != last_product_order.id:
                        message = _("Please, recalculate prepaid discount")
            if message:
                raise exceptions.Warning(message)
        return super().action_confirm()

    @api.multi
    def calculate_prepaid_discount(self):
        # Comprobar qué descuento le corresponde
        # Si margen_pedido < margin_discount_1 -> No le corresponde descuento
        # Si margin_1 < margen_pedido < margin_2 -> Le corresponde descuento discount_1
        # Si margen_pedido > margin_2 -> Le corresponde descuento discount_2
        margin_discount_1 = self.env['ir.config_parameter'].sudo().get_param('minimum_margin.discount_perc.prepaid_1')
        margin_discount_2 = self.env['ir.config_parameter'].sudo().get_param('minimum_margin.discount_perc.prepaid_2')
        prepaid_discount_product_id = self.env.ref('prepaid_order_discount.prepaid_discount_product').id
        shipping_cost_categ = self.env['product.category'].\
            with_context(lang='es_ES').search([('name', '=', 'Portes')])
        for sale in self:
            # Comprobar que el plazo de pago del cliente no sea prepago por defecto,
            # en cuyo caso no le corresponde este descuento
            if sale.partner_id.prepaid_payment_term():
                sale.cancel_prepaid_option()
                continue
            # Borrar línea descuento prepago existente
            sale.order_line.filtered(lambda l: l.product_id.id == prepaid_discount_product_id).unlink()
            # Aplicar promociones
            sale.apply_commercial_rules()
            # Obtener umbrales márgenes y porcentaje descuento a aplicar
            margin_sale = sale.margin_rappel
            margin_1 = int(margin_discount_1.split(',')[0])
            discount_1 = margin_discount_1.split(',')[1]
            margin_2 = int(margin_discount_2.split(',')[0])
            discount_2 = margin_discount_2.split(',')[1]

            amount_untaxed = sum(sale.order_line.filtered(
                lambda l: l.product_id.categ_id.id not in shipping_cost_categ.ids).mapped('price_subtotal'))
            if margin_1 < margin_sale < margin_2:
                last_sequence = sale.order_line.sorted(lambda l: l.sequence)[-1].sequence
                discount_line_vals = {'order_id': sale.id,
                                      'product_id': prepaid_discount_product_id,
                                      'name': _("%s prepaid discount") % (discount_1 + '%'),
                                      'product_uom_qyt': 1.0,
                                      'price_unit': -(amount_untaxed*int(discount_1)/100),
                                      'sequence': last_sequence + 1}
                self.env['sale.order.line'].create(discount_line_vals)
            elif margin_sale > margin_2:
                last_sequence = sale.order_line.sorted(lambda l: l.sequence)[-1].sequence
                discount_line_vals = {'order_id': sale.id,
                                      'product_id': prepaid_discount_product_id,
                                      'name': _("%s prepaid discount") % (discount_2 + '%'),
                                      'product_uom_qyt': 1.0,
                                      'price_unit': -(amount_untaxed*int(discount_2)/100),
                                      'sequence': last_sequence + 1}
                self.env['sale.order.line'].create(discount_line_vals)
        return True

    @api.multi
    def cancel_prepaid_option(self):
        for sale in self:
            # Borrar línea descuento prepago existente
            prepaid_discount_product_id = self.env.ref('prepaid_order_discount.prepaid_discount_product').id
            sale.order_line.filtered(lambda l: l.product_id.id == prepaid_discount_product_id).unlink()
            # Marcar check prepaid_discount = False
            sale.prepaid_option = False
        return True

