# © 2014 Pexego Sistemas Informáticos
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class ProductCategory(models.Model):

    _inherit = 'product.category'

    percent = fields.Float(string="Outlet Percent",
                           help="This outlet percent will be used when a product moves to an outlet category")

    @api.constrains('percent')
    def check_length(self):
        for categ in self:
            percent = categ.percent
            if (percent > 100) | (percent < 0):
                raise ValidationError(
                    _('Error ! The outlet percent values must be'
                      'between 0 and 100'))
        return True


class ProductProduct(models.Model):

    _inherit = 'product.product'

    is_outlet = fields.Boolean('Is outlet', compute='_is_outlet')
    normal_product_id = fields.Many2one('product.product', 'normal product')
    outlet_product_ids = fields.One2many('product.product',
                                         'normal_product_id',
                                         'Outlet products')

    def _is_outlet(self):
        outlet_cat = self.env.ref('product_outlet.product_category_outlet')
        for product in self:
            if product.categ_id == outlet_cat or \
                    product.categ_id.parent_id == outlet_cat:
                product.is_outlet = True
            else:
                product.is_outlet = False

    @api.model
    def cron_update_outlet_price_and_discontinued_products(self):
        outlet_categ_ids = []
        outlet_categ_ids.append(self.env.ref('product_outlet.product_category_o1').id)
        outlet_categ_ids.append(self.env.ref('product_outlet.product_category_o2').id)
        outlet_products = self.env['product.product'].search([('categ_id', 'in', outlet_categ_ids),
                                                              "|",('normal_product_id.list_price1', '!=', 0),
                                                              ('normal_product_id.list_price2', '!=', 0),
                                                              "|",('qty_available', '>' ,0),('sale_ok', '=', True)],
                                                             order="id desc")
        for product_o in outlet_products:
            origin_product = product_o.normal_product_id
            standard_price = origin_product.standard_price * (1 - product_o.categ_id.percent / 100)
            standard_price_2 = origin_product.standard_price_2 * (1 - product_o.categ_id.percent / 100)

            # update all prices
            for item in product_o.item_ids:
                item.fixed_price = origin_product.with_context(pricelist=item.pricelist_id.id).price * \
                                   (1 - (product_o.categ_id.percent / 100))

            values = product_o.get_list_updated_prices()
            values.update({
                'standard_price': standard_price,
                'standard_price_2': standard_price_2,
                'commercial_cost': origin_product.commercial_cost,
                'sale_ok': product_o.qty_available>0
            })

            product_o.write(values)

        discontinued_products = self.env['product.product'].search(
            [('discontinued', '=', True), ('qty_available', '>', 0)])
        discontinued_products.write({'sale_ok': True,'discontinued':False})


