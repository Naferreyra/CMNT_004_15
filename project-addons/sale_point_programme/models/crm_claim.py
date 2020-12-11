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


class CrmClaimRma(models.Model):
    _inherit = 'crm.claim'

    @api.multi
    def make_refund_invoice(self):
        for claim_obj in self:
            dicc_invoice_product = {}
            dicc_claim_line_invoice = {}
            for line in claim_obj.claim_inv_line_ids:
                if not line.invoiced:
                    if dicc_invoice_product.get(line.invoice_id):
                        dicc_invoice_product[line.invoice_id] += [line.product_id.id]
                    else:
                        dicc_invoice_product[line.invoice_id] = [line.product_id.id]
                    if dicc_claim_line_invoice.get(line.invoice_id):
                        dicc_claim_line_invoice[line.invoice_id] += [line]
                    else:
                        dicc_claim_line_invoice[line.invoice_id] = [line]
            sale_order = self.env['sale.order']
            dicc_claim_line_order = {}
            for invoice, product_ids in dicc_invoice_product.items():
                for order in invoice.sale_order_ids:
                    sale_order += order
                    if dicc_claim_line_order.get(order):
                        dicc_claim_line_order[order] += dicc_claim_line_invoice[invoice]
                    else:
                        dicc_claim_line_order[order] = dicc_claim_line_invoice[invoice]
            obj_bag = self.env['res.partner.point.programme.bag']
            for order in sale_order:
                bag_ids = obj_bag.search([('order_id', '=', order.id)])
                if bag_ids:
                    rules = bag_ids.mapped('point_rule_id')
                    rules_with_points, brands, products, categories = order.compute_points_programme_bag(
                        dicc_claim_line_order.get(order), rules, "claim")
                    for rule, points in rules_with_points.items():
                        modality_type = rule.modality
                        if ((rule.product_brand_id.id in brands) | (rule.product_id.id in products) |
                            (rule.category_id.id in categories)) and modality_type == 'point' and points:
                            obj_bag.create({'name': rule.name,
                                            'point_rule_id': rule.id,
                                            'order_id': order.id,
                                            'points': -points,
                                            'partner_id': order.partner_id.id})

        return super(CrmClaimRma, self).make_refund_invoice()
