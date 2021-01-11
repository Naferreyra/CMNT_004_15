##############################################################################
#
#    Copyright (C) 2016 Comunitea Servicios Tecnológicos S.L.
#    $Omar Castiñeira Saavedra$ <omar@comunitea.com>
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

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp


class ProductTemplate(models.Model):

    _inherit = "product.template"

    standard_price_2 = fields.Float(
        digits=dp.get_precision('Product Price'),
        string="Cost Price 2", company_dependent=True)

    def recalculate_standard_price_2(self):
        for product in self:
            moves = self.env['stock.move'].search(
                [('product_id', 'in', product.product_variant_ids._ids),
                ('remaining_qty', '>', 0)])
            if sum(moves.mapped('remaining_qty')) != 0:
                standard_price_2 = sum(moves.mapped('remaining_value')) / sum(moves.mapped('remaining_qty'))
                dp = self.env['decimal.precision'].search([('name', '=', 'Product Price')])
                standard_price_2 = round(standard_price_2, dp.digits)
                if standard_price_2 != round(product.standard_price_2, dp.digits):
                    product.standard_price_2 = standard_price_2 or product.standard_price
                elif not standard_price_2:
                    product.standard_price_2 = product.standard_price
            else:
                product.standard_price_2 = product.standard_price
            bom_ids = self.env['mrp.bom']
            if product.product_variant_ids.used_in_bom_count:
                bom_ids += self.env['mrp.bom'].search([('bom_line_ids.product_id', '=', product.product_variant_ids.id)])
            if product.product_variant_ids.bom_ids:
                bom_ids += product.product_variant_ids.bom_ids.filtered(lambda b: b.product_tmpl_id)

            if bom_ids:
                for bom in bom_ids:
                    cost = 0.0
                    for bom_line in bom.bom_line_ids:
                        cost += bom_line.product_id.standard_price_2 * bom_line.product_qty
                    bom.product_tmpl_id.write({'standard_price_2': cost})
                    bom.product_tmpl_id.product_variant_ids._onchange_cost_increment()

            product.product_variant_ids._onchange_cost_increment()


class ProductProduct(models.Model):
    _inherit = 'product.product'

    standard_price_2_inc = fields.Float(
        digits=dp.get_precision('Product Price'),
        string="Cost Price 2")
    cost_increment = fields.Float("Increment", default=0.0)

    @api.onchange("cost_increment")
    def _onchange_cost_increment(self):
        self.standard_price_2_inc = self.standard_price_2 + self.cost_increment

    @api.depends('list_price', 'pvd1_relation', 'pvd2_relation', 'pvd3_relation', 'pvd4_relation', 'pvd5_relation',
                 'standard_price_2', 'pvi1_price', 'pvi2_price', 'pvi3_price', 'pvi4_price', 'pvi5_price')
    def _get_margins(self):
        for product in self:
            if product.list_price and product.pvd1_relation:
                product.margin_pvd1 = \
                    (1 - (product.standard_price_2 /
                        (product.list_price * product.pvd1_relation))) * 100.0

            if product.list_price2 and product.pvd2_relation:
                product.margin_pvd2 = \
                    (1 - (product.standard_price_2 /
                        (product.list_price2 * product.pvd2_relation))) * \
                    100.0

            if product.list_price3 and product.pvd3_relation:
                product.margin_pvd3 = \
                    (1 - (product.standard_price_2 /
                         (product.list_price3 * product.pvd3_relation))) * \
                    100.0

            if product.list_price4 and product.pvd4_relation:
                product.margin_pvd4 = \
                    (1 - (product.standard_price_2 /
                        (product.list_price4 * product.pvd4_relation))) * \
                    100.0

            if product.list_price5 and product.pvd5_relation:
                product.margin_pvd5 = \
                    (1 - (product.standard_price_2 /
                        (product.list_price5 * product.pvd5_relation))) * \
                    100.0

            if product.pvi1_price:
                product.margin_pvi1 = \
                    (1 - (product.standard_price_2 / product.pvi1_price)) * 100.0
                if product.pvd1_price:
                    product.margin_pvd_pvi_1 = \
                        ((product.pvd1_price - product.pvi1_price) / product.pvd1_price) * 100

            if product.pvi2_price:
                product.margin_pvi2 = \
                    (1 - (product.standard_price_2 / product.pvi2_price)) * 100.0
                if product.pvd2_price:
                    product.margin_pvd_pvi_2 = \
                        ((product.pvd2_price - product.pvi2_price) / product.pvd2_price) * 100

            if product.pvi3_price:
                product.margin_pvi3 = \
                    (1 - (product.standard_price_2 / product.pvi3_price)) * 100.0
                if product.pvd3_price:
                    product.margin_pvd_pvi_3 = \
                        ((product.pvd3_price - product.pvi3_price) / product.pvd3_price) * 100

            if product.pvi4_price:
                product.margin_pvi4 = \
                    (1 - (product.standard_price_2 / product.pvi4_price)) * 100.0
                if product.pvd4_price:
                    product.margin_pvd_pvi_4 = \
                        ((product.pvd4_price - product.pvi4_price) / product.pvd4_price) * 100

            if product.pvi5_price:
                product.margin_pvi5 = \
                    (1 - (product.standard_price_2 / product.pvi5_price)) * 100.0
                if product.pvd5_price:
                    product.margin_pvd_pvi_5 = \
                        ((product.pvd5_price - product.pvi5_price) / product.pvd5_price) * 100

    list_price1 = fields.Float('Sale Price 1', digits=dp.get_precision('Product Price'))
    list_price2 = fields.Float('Sale Price 2', digits=dp.get_precision('Product Price'))
    list_price3 = fields.Float('Sale Price 3', digits=dp.get_precision('Product Price'))
    list_price4 = fields.Float('Sale Price 4', digits=dp.get_precision('Product Price'))
    list_price5 = fields.Float('Sale Price 5', digits=dp.get_precision('Product Price'))

    commercial_cost = fields.Float('Commercial Cost', digits=dp.get_precision('Product Price'))

    pvd1_relation = fields.Float('PVP/PVD 1 relation', digits=(4, 2), default=0.5)
    pvd2_relation = fields.Float('PVP 2 / PVD 2 relation', digits=(4, 2), default=0.5)
    pvd3_relation = fields.Float('PVP 3 / PVD 3 relation', digits=(4, 2), default=0.5)
    pvd4_relation = fields.Float('PVP 4 / PVD 4 relation', digits=(4, 2), default=0.5)
    pvd5_relation = fields.Float('PVP 5 / PVD 5 relation', digits=(4, 2), default=0.5)

    pvd1_price = fields.Float('PVD 1 price', digits=dp.get_precision('Product Price'))
    pvd2_price = fields.Float('PVD 2 price', digits=dp.get_precision('Product Price'))
    pvd3_price = fields.Float('PVD 3 price', digits=dp.get_precision('Product Price'))
    pvd4_price = fields.Float('PVD 4 price', digits=dp.get_precision('Product Price'))
    pvd5_price = fields.Float('PVD 5 price', digits=dp.get_precision('Product Price'))

    pvi1_price = fields.Float('PVI 1 price', digits=dp.get_precision('Product Price'))
    pvi2_price = fields.Float('PVI 2 price', digits=dp.get_precision('Product Price'))
    pvi3_price = fields.Float('PVI 3 price', digits=dp.get_precision('Product Price'))
    pvi4_price = fields.Float('PVI 4 price', digits=dp.get_precision('Product Price'))
    pvi5_price = fields.Float('PVI 5 price', digits=dp.get_precision('Product Price'))

    pvm1_price = fields.Float('PVM 1 price', digits=dp.get_precision('Product Price'))
    pvm2_price = fields.Float('PVM 2 price', digits=dp.get_precision('Product Price'))
    pvm3_price = fields.Float('PVM 3 price', digits=dp.get_precision('Product Price'))

    margin_pvd1 = fields.Float(computed='_get_margins',
                               string="PVD 1 Margin",
                               digits=(5, 2),
                               store=True)
    margin_pvd2 = fields.Float(computed='_get_margins',
                               string="PVD 2 Margin",
                               digits=(5, 2),
                               store=True)
    margin_pvd3 = fields.Float(computed='_get_margins',
                               string="PVD 3 Margin",
                               digits=(5, 2),
                               store=True)
    margin_pvd4 = fields.Float(computed='_get_margins',
                               string="PVD 4 Margin",
                               digits=(5, 2),
                               store=True)
    margin_pvd5 = fields.Float(computed='_get_margins',
                               string="PVD 5 Margin",
                               digits=(5, 2),
                               store=True)
    margin_pvi1 = fields.Float(computed='_get_margins',
                               string="PVI 1 Margin",
                               digits=(5, 2),
                               store=True)
    margin_pvi2 = fields.Float(computed='_get_margins',
                               string="PVI 2 Margin",
                               digits=(5, 2),
                               store=True)
    margin_pvi3 = fields.Float(computed='_get_margins',
                               string="PVI 3 Margin",
                               digits=(5, 2),
                               store=True)
    margin_pvi4 = fields.Float(computed='_get_margins',
                               string="PVI 4 Margin",
                               digits=(5, 2),
                               store=True)
    margin_pvi5 = fields.Float(computed='_get_margins',
                               string="PVI 5 Margin",
                               digits=(5, 2),
                               store=True)
    margin_pvd_pvi_1 = fields.Float(computed='_get_margins',
                                    string='PVD/PVI 1 margin',
                                    digits=(5, 2),
                                    store=True)
    margin_pvd_pvi_2 = fields.Float(computed='_get_margins',
                                    string='PVD/PVI 2 margin',
                                    digits=(5, 2),
                                    store=True)
    margin_pvd_pvi_3 = fields.Float(computed='_get_margins',
                                    string='PVD/PVI 3 margin',
                                    digits=(5, 2),
                                    store=True)
    margin_pvd_pvi_4 = fields.Float(computed='_get_margins',
                                    string='PVD/PVI 4 margin',
                                    digits=(5, 2),
                                    store=True)
    margin_pvd_pvi_5 = fields.Float(computed='_get_margins',
                                    string='PVD/PVI 5 margin',
                                    digits=(5, 2),
                                    store=True)

    @api.onchange('pvd1_price')
    def pvd1_price_change(self):
        pvd1_relation = 0.5
        if self.pvd1_price:
            self.lst_price = (1.0 / pvd1_relation) * self.pvd1_price
            self.margin_pvd1 = (1 - (self.standard_price_2 / self.pvd1_price)) * 100.0
            self.margin_pvd_pvi_1 = ((self.pvd1_price - self.pvi1_price) / self.pvd1_price) * 100
        else:
            self.lst_price = 0
            self.margin_pvd1 = 0
            self.margin_pvd_pvi_1 = 0

    @api.onchange('pvd2_price')
    def pvd2_price_change(self):
        pvd2_relation = 0.5
        if self.pvd2_price:
            self.list_price2 = (1.0 / pvd2_relation) * self.pvd2_price
            self.margin_pvd2 = (1 - (self.standard_price_2 / self.pvd2_price)) * 100.0
            self.margin_pvd_pvi_2 = ((self.pvd2_price - self.pvi2_price) / self.pvd2_price) * 100
        else:
            self.list_price2 = 0
            self.margin_pvd2 = 0
            self.margin_pvd_pvi_2 = 0

    @api.onchange('pvd3_price')
    def pvd3_price_change(self):
        pvd3_relation = 0.5
        if self.pvd3_price:
            self.list_price3 = (1.0 / pvd3_relation) * self.pvd3_price
            self.margin_pvd3 = (1 - (self.standard_price_2 / self.pvd3_price)) * 100.0
            self.margin_pvd_pvi_3 = ((self.pvd3_price - self.pvi3_price) / self.pvd3_price) * 100
        else:
            self.list_price3 = 0
            self.margin_pvd3 = 0
            self.margin_pvd_pvi_3 = 0

    @api.onchange('pvd4_price')
    def pvd4_price_change(self):
        pvd4_relation = 0.5
        if self.pvd4_price:
            self.list_price4 = (1.0 / pvd4_relation) * self.pvd4_price
            self.margin_pvd4 = (1 - (self.standard_price_2 / self.pvd4_price)) * 100.0
            self.margin_pvd_pvi_4 = ((self.pvd4_price - self.pvi4_price) / self.pvd4_price) * 100
        else:
            self.list_price4 = 0
            self.margin_pvd4 = 0
            self.margin_pvd_pvi_4 = 0

    @api.onchange('pvd5_price')
    def pvd5_price_change(self):
        pvd5_relation = 0.5
        if self.pvd5_price:
            self.list_price5 = (1.0 / pvd5_relation) * self.pvd5_price
            self.margin_pvd5 = (1 - (self.standard_price_2 / self.pvd5_price)) * 100.0
            self.margin_pvd_pvi_5 = ((self.pvd5_price - self.pvi5_price) / self.pvd5_price) * 100
        else:
            self.list_price5 = 0
            self.margin_pvd5 = 0
            self.margin_pvd_pvi_5 = 0

    @api.onchange('pvi1_price')
    def pvi1_price_change(self):
        if self.pvd1_price:
            self.margin_pvd_pvi_1 = ((self.pvd1_price - self.pvi1_price) / self.pvd1_price) * 100
        else:
            self.margin_pvd_pvi_1 = 0

        if self.pvi1_price:
            self.margin_pvi1 = (1 - (self.standard_price_2 / self.pvi1_price)) * 100.0
        else:
            self.margin_pvi1 = 0

    @api.onchange('pvi2_price')
    def pvi2_price_change(self):
        if self.pvd2_price:
            self.margin_pvd_pvi_2 = ((self.pvd2_price - self.pvi2_price) / self.pvd2_price) * 100
        else:
            self.margin_pvd_pvi_2 = 0

        if self.pvi2_price:
            self.margin_pvi2 = (1 - (self.standard_price_2 / self.pvi2_price)) * 100.0
        else:
            self.margin_pvi2 = 0

    @api.onchange('pvi3_price')
    def pvi3_price_change(self):
        if self.pvd3_price:
            self.margin_pvd_pvi_3 = ((self.pvd3_price - self.pvi3_price) / self.pvd3_price) * 100
        else:
            self.margin_pvd_pvi_3 = 0

        if self.pvi3_price:
            self.margin_pvi3 = (1 - (self.standard_price_2 / self.pvi3_price)) * 100.0
        else:
            self.margin_pvi3 = 0

    @api.onchange('pvi4_price')
    def pvi4_price_change(self):
        if self.pvd4_price:
            self.margin_pvd_pvi_4 = ((self.pvd4_price - self.pvi4_price) / self.pvd4_price) * 100
        else:
            self.margin_pvd_pvi_4 = 0

        if self.pvi4_price:
            self.margin_pvi4 = (1 - (self.standard_price_2 / self.pvi4_price)) * 100.0
        else:
            self.margin_pvi4 = 0

    @api.onchange('pvi5_price')
    def pvi5_price_change(self):
        if self.pvd5_price:
            self.margin_pvd_pvi_5 = ((self.pvd5_price - self.pvi5_price) / self.pvd5_price) * 100
        else:
            self.margin_pvd_pvi_5 = 0

        if self.pvi5_price:
            self.margin_pvi5 = (1 - (self.standard_price_2 / self.pvi5_price)) * 100.0
        else:
            self.margin_pvi5 = 0
