##############################################################################
#
#    Copyright (C) 2004-2014 Pexego Sistemas Informáticos All Rights Reserved
#    $Marta Vázquez Rodríguez$ <marta@pexego.es>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, models, fields, _
from odoo.tools.misc import ustr
from odoo.exceptions import except_orm, UserError


class PromotionsRulesConditionsExprs(models.Model):
    _inherit = 'promos.rules.conditions.exps'

    attribute = fields.Selection(
        selection_add=[
            ('prod_tag', 'Tag in order'),
            ('order_pricelist', _('Order Pricelist')),
            ('web_discount', 'Web Discount')])

    def on_change_attribute(self):
        if not self.attribute:
            return
        if self.attribute == 'prod_tag':
            self.value = 'prod_tag'

        if self.attribute in ['order_pricelist']:
            self.value = 'pricelist_name'

        if self.attribute == 'web_discount':
            self.value = 'True'
        return super().on_change_attribute()

    def validate(self, vals):
        numerical_comparators = ['==', '!=', '<=', '<', '>', '>=']
        attribute = vals['attribute']
        comparator = vals['comparator']
        if attribute == 'web_discount' and \
                comparator not in numerical_comparators:
            raise UserError("Only %s can be used with %s"
                            % (",".join(numerical_comparators), attribute))
        if attribute == 'prod_tag' and comparator not in numerical_comparators:
            raise UserError("Only %s can be used with %s"
                            % (",".join(numerical_comparators), attribute))
        return super().validate(vals)

    def serialise(self, attribute, comparator, value):
        """
        Constructs an expression from the entered values
        which can be quickly evaluated
        @param attribute: attribute of promo expression
        @param comparator: Comparator used in promo expression.
        @param value: value according which attribute will be compared
        """

        if attribute == 'prod_tag':
            return '%s %s prod_tag' % (value, comparator)
        elif attribute == 'order_pricelist':
            return """order.pricelist_id.name %s %s""" % (comparator, value)
        elif attribute == 'web_discount':
            return "kwargs['%s']" % attribute
        else:
            return super().serialise(attribute, comparator, value)

    def evaluate(self, order, **kwargs):
        prod_tag = {}
        web_discount = False

        for line in order.order_line:
            if line.product_id:
                prod_tag = line.product_tags
                if line.web_discount:
                    web_discount = True
        return super().evaluate(
            order, prod_tag=prod_tag, web_discount=web_discount, **kwargs)


class PromotionsRulesActions(models.Model):
    _inherit = 'promos.rules.actions'

    action_type = fields.Selection(
        selection_add=[
            ('prod_disc_perc_accumulated',
             _('Discount % on Product accumulated')),
            ('tag_disc_perc',
             _('Discount % on Tag')),
            ('tag_disc_perc_accumulated',
             _('Discount % on Tag accumulated')),
            ('categ_disc_perc',
             _('Discount % on Category')),
            ('categ_disc_perc_accumulated',
             _('Discount % on Categ accumulated')),
            ('brand_disc_perc',
             _('Discount % on Brand')),
            ('brand_disc_perc_accumulated',
             _('Discount % on Brand accumulated')),
            ('web_disc_accumulated',
             _('Web Discount % on Product accumulated')),
            ('a_get_b_product_tag',
             _('AxB on product tag')),
            ('prod_fixed_price_tag',
             _('Fixed price on Product Tag')),
            ('prod_fixed_price',
             _('Fixed price on Product'))
            ])

    def on_change(self):
        if self.action_type == 'prod_disc_perc_accumulated':
            self.product_code = 'product_code'
            self.arguments = '0.00'

        elif self.action_type in [
                'tag_disc_perc', 'tag_disc_perc_accumulated']:
            self.product_code = 'tag_name'
            self.arguments = '0.00'

        elif self.action_type in [
                'categ_disc_perc', 'categ_disc_perc_accumulated']:
            self.product_code = 'categ_code'
            self.arguments = '0.00'

        elif self.action_type in [
                'brand_disc_perc', 'brand_disc_perc_accumulated']:
            self.product_code = 'brand_code'
            self.arguments = '0.00'

        elif self.action_type == 'web_disc_accumulated':
            self.arguments = '10.00'

        elif self.action_type == 'a_get_b_product_tag':
            self.product_code = 'product_tag'
            self.arguments = 'A,B'

        elif self.action_type == 'prod_fixed_price_tag':
            self.product_code = 'product_tag'
            self.arguments = '0.00'

        elif self.action_type == 'prod_fixed_price':
            self.product_code = 'product_reference'
            self.arguments = '0.00'

        return super().on_change()

    def apply_perc_discount_accumulated(self, order_line):
        final_discount = eval(self.arguments)
        if order_line.discount:
            price_discounted = order_line.price_unit * (
                1 - (order_line.discount or 0.0) / 100.0)
            new_price_unit = price_discounted * \
                (1 - (eval(self.arguments) / 100.0))
            final_discount = 100.0 - (new_price_unit * 100.0 /
                                      order_line.price_unit)
        if order_line.accumulated_promo:
            order_line.write({'discount': final_discount})
        else:
            order_line.write({'discount': final_discount,
                              'old_discount': order_line.discount,
                              'accumulated_promo': True})

    def action_tag_disc_perc_accumulated(self, order):
        """
        Action for 'Discount % on Product'
        @param cursor: Database Cursor
        @param user: ID of User
        @param action: Action to be taken on sale order
        @param order: sale order
        @param context: Context(no direct use).
        """
        for order_line in order.order_line:
            if eval(self.product_code) in order_line.product_tags:
                self.apply_perc_discount_accumulated(order_line)
        return {}

    def action_categ_disc_perc_accumulated(self, order):
        for order_line in order.order_line:
            if eval(self.product_code) == \
                    order_line.product_id.categ_id.code:
                self.apply_perc_discount_accumulated(order_line)
        return {}

    def action_brand_disc_perc_accumulated(self, order):
        for order_line in order.order_line:
            if eval(self.product_code) == \
                    order_line.product_id.product_brand_id.code:
                self.apply_perc_discount_accumulated(order_line)
        return {}

    def action_prod_disc_perc_accumulated(self, order):
        for order_line in order.order_line:
            if order_line.product_id.code == eval(self.product_code):
                self.apply_perc_discount_accumulated(order_line)

    def apply_perc_discount(self, order_line):
        vals = {
            'discount': eval(self.arguments),
            'old_discount': order_line.discount
        }
        return order_line.write(vals)

    def action_tag_disc_perc(self, order):
        """
        Action for 'Discount % on Product'
        @param cursor: Database Cursor
        @param user: ID of User
        @param action: Action to be taken on sale order
        @param order: sale order
        @param context: Context(no direct use).
        """
        for order_line in order.order_line:
            if eval(self.product_code) in order_line.product_tags:
                self.apply_perc_discount(order_line)
        return {}

    def action_categ_disc_perc(self, order):
        for order_line in order.order_line:
            if eval(self.product_code) == \
                    order_line.product_id.categ_id.code:
                self.apply_perc_discount(order_line)
        return {}

    def action_brand_disc_perc(self, order):
        for order_line in order.order_line:
            if eval(self.product_code) == \
                    order_line.product_id.product_brand_id.code:
                self.apply_perc_discount(order_line)
        return {}

    def action_web_disc_accumulated(self, order):
        for order_line in order.order_line:
            if order_line.web_discount:
                self.apply_perc_discount_accumulated(order_line)
        return {}

    def action_a_get_b_product_tag(self, order):
        promo_products = []
        qty_a, qty_b = [eval(arg) for arg in self.arguments.split(",")]
        for order_line in order.order_line.filtered(
                lambda l: not l.promotion_line):
            if order_line.product_id.id not in promo_products:
                if eval(self.product_code) in order_line.product_id.tag_ids.mapped('name'):
                    qty = 0
                    for order_line_2 in order.order_line:
                        if order_line_2.product_id.id == order_line.product_id.id:
                            qty += order_line_2.product_uom_qty
                    num_lines = int(qty / qty_a) * (qty_a - qty_b)
                    if qty - qty_a >= 0:
                        self.create_y_line_axb(
                            order, order_line,num_lines)
                        promo_products.append(order_line.product_id.id)
        return {}

    def action_prod_fixed_price_tag(self, order):
        for order_line in order.order_line:
            if eval(self.product_code) in order_line.product_tags:
                self.apply_fixed_price(order_line)
        return {}

    def action_prod_fixed_price(self, order):
        for order_line in order.order_line:
            if order_line.product_id.default_code in eval(self.product_code):
                self.apply_fixed_price(order_line)
        return {}

    def apply_fixed_price(self, order_line):
        vals = {
            'price_unit': eval(self.arguments)
        }
        return order_line.write(vals)

    def create_y_line_axb(self, order, order_line, quantity):
        product_id=order_line.product_id
        vals = {
            'order_id': order.id,
            'sequence': order_line.sequence,
            'product_id': self.env.ref('commercial_rules.product_discount').id,
            'name': '%s (%s)' % (
                     product_id.default_code,
                     self.promotion.line_description),
            'price_unit': -order_line.price_unit,
            'discount': order_line.discount,
            'promotion_line': True,
            'product_uom_qty': quantity,
            'product_uom': product_id.uom_id.id,
            'original_line_id_promo': order_line.id,
            'promo_qty_split': eval(self.arguments.split(",")[0])

        }
        self.create_line(vals)
        return True


class PromotionsRules(models.Model):

    _inherit = "promos.rules"

    special_promo = fields.Boolean("Special Promo")

    line_description = fields.Char(translate=True,string="Desciption in lines",help="This field is shown in the description field of the invoice,picking and sale lines")

    @api.model
    def apply_special_promotions(self, order):
        active_promos = self.search([('special_promo', '=', True)])

        for promotion_rule in active_promos:
            result = promotion_rule.evaluate(order)
            #If evaluates to true
            if result:
                try:
                    promotion_rule.execute_actions(order)
                except Exception as e:
                    raise except_orm("Promotions", ustr(e))
                #If stop further is true
                if promotion_rule.stop_further:
                    return True
        return True
