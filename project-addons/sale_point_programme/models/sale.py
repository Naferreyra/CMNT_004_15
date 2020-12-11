##############################################################################
#
#    Copyright (C) 2014 Pexego Sistemas Informáticos All Rights Reserved
#    $Omar Castiñeira Saavedra <omar@pexego.es>$
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

from odoo import models, api, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def compute_points_programme_bag(self, lines, rules, mode="order"):
        total_product_qty = 0.0
        categories = {}
        products = {}
        brands = {}

        rules_with_points = {}

        if rules:
            for line in lines:
                if line.product_id:
                    pkey = line.product_id.id
                    ckey = line.product_id.categ_id.id
                    bkey = line.product_id.product_brand_id.id
                    if mode == "claim":
                        qty = line.qty
                    else:
                        qty = line.product_uom_qty
                    if mode == "move":
                        amount = line.sale_line_id.price_subtotal / line.sale_line_id.product_uom_qty * line.product_uom_qty
                    else:
                        amount = line.price_subtotal
                    if products.get(pkey):
                        products[pkey]['qty'] += qty
                        products[pkey]['amount'] += amount
                    else:
                        products[pkey] = {'qty': qty,
                                          'amount': amount}
                    if categories.get(ckey):
                        categories[ckey]['qty'] += qty
                        categories[ckey]['amount'] += amount
                    else:
                        categories[ckey] = {'qty': qty,
                                            'amount': amount}
                    if brands.get(bkey):
                        brands[bkey]['qty'] += qty
                        brands[bkey]['amount'] += amount
                    else:
                        brands[bkey] = {'qty': qty,
                                        'amount': amount}
                    total_product_qty += qty

            for rule in rules:
                apply_rule = True
                if rule.partner_category_id:
                    apply_rule = rule.partner_category_id in self.partner_id.category_id
                if apply_rule:
                    points = False
                    if rule.product_id:
                        if rule.product_id.id in products:
                            record = products[rule.product_id.id]
                            if rule.attribute == 'product_qty':
                                points = rule.evaluate(record['qty'])
                            else:
                                points = rule.evaluate(record['amount'])
                    elif rule.category_id:
                        if rule.category_id.id in categories:
                            record = categories[rule.category_id.id]
                            if rule.attribute == 'product_qty':
                                points = rule.evaluate(record['qty'])
                            else:
                                points = rule.evaluate(record['amount'])
                    elif rule.product_brand_id:
                        if rule.product_brand_id.id in brands:
                            record = brands[rule.product_brand_id.id]
                            if rule.attribute == 'product_qty':
                                points = rule.evaluate(record['qty'])
                            else:
                                points = rule.evaluate(record['amount'])
                    elif rule.attribute == 'amount_untaxed':
                        points = rule.evaluate(self.amount_untaxed)
                    else:
                        points = rule.evaluate(total_product_qty)
                    rules_with_points[rule] = points
        return rules_with_points, brands, products, categories

    @api.multi
    def action_confirm(self):
        res = super().action_confirm()
        if isinstance(res, bool):
            bag_obj = self.env['res.partner.point.programme.bag']
            for order in self:
                rule_obj = self.env['sale.point.programme.rule']
                rules = rule_obj.search(['|', ('date_start', '<=', self.date_order[:10]),
                                         ('date_start', '=', False),
                                         '|', ('date_end', '>=', self.date_order[:10]),
                                         ('date_end', '=', False)])
                rules_with_points, brands, products, categories = order.compute_points_programme_bag(self.order_line,
                                                                                                     rules)
                for rule, points in rules_with_points.items():
                    modality_type = rule.modality
                    if modality_type == 'participation':
                        reg = bag_obj.search_read([('point_rule_id', '=', rule.id)], ['points'],
                                                  order='id desc', limit=1)
                        if not reg:
                            last_number = 0
                        else:
                            last_number = reg[0]['points']

                        control = 0
                        while points > control:
                            participation = last_number + 1

                            if order.partner_id.is_company or not order.partner_id.parent_id:
                                partner_id = order.partner_id.id
                            else:
                                partner_id = order.partner_id.parent_id.id

                            bag_obj.create({'name': rule.name,
                                            'point_rule_id': rule.id,
                                            'order_id': order.id,
                                            'points': participation,
                                            'partner_id': partner_id})
                            last_number = participation
                            control += 1
                    elif modality_type == 'point':
                        if points:
                            if order.partner_id.is_company or not order.partner_id.parent_id:
                                partner_id = order.partner_id.id
                            else:
                                partner_id = order.partner_id.parent_id.id

                            bag_obj.create({'name': rule.name,
                                            'point_rule_id': rule.id,
                                            'order_id': order.id,
                                            'points': points,
                                            'partner_id': partner_id})

        return res

    @api.multi
    def action_cancel(self):
        self.ensure_one()
        res = super(SaleOrder, self).action_cancel()
        for line in self.order_line:
            if line.bag_ids:
                line.bag_ids.write({'applied_state': 'no', 'order_applied_id': False})
        return res

    # Para el cron que envia los emails
    @api.model
    def send_participations(self):
        bag_obj = self.env['res.partner.point.programme.bag']
        registro = self.env['res.partner.point.programme.bag'].search_read([('email_sent', '=', False)],
                                                                           [('partner_id'), ('order_id'), ('points')])

        # Obtener en diccionario los pedidos de los partners
        partners = {}
        for partner in registro:
            records = {}
            partner_id = partner['partner_id'][0]
            order_id = partner['order_id'][1]
            if partner['partner_id'][0] not in partners:
                records[order_id] = [partner['points']]
                partners[partner_id] = records
            elif partner['partner_id'][0] in partners:
                if order_id in partners[partner_id]:
                    partners[partner_id][order_id].append(partner['points'])
                else:
                    records[order_id] = [partner['points']]
                    partners[partner_id][order_id] = [partner['points']]

        obj_partner = self.env['res.partner']
        for item in partners:
            partner = obj_partner.browse(item)

            mail_pool = self.env['mail.mail']
            template_obj = self.env.ref('sale_point_programme.template_participations')
            ctx = dict(self._context)
            ctx.update({
                'values': partners[partner.id]
            })
            mail_id = template_obj.with_context(ctx).send_mail(partner.id)

            if mail_id:
                mail_id_check = mail_pool.browse(mail_id)
                mail_id_check.send()

        sent_it = bag_obj.search([('email_sent', '=', False)])
        for line in sent_it:
            line.write({'email_sent': True})

        return True


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    bag_ids = fields.One2many(
        comodel_name='res.partner.point.programme.bag',
        inverse_name='line_id',
        string='Point Bag'
    )

    @api.multi
    def unlink(self):
        for line in self:
            if line.bag_ids:
                line.bag_ids.write({'applied_state': 'no', 'order_applied_id': False, 'line_id': False})
        return super(SaleOrderLine, self).unlink()
