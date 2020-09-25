# © 2019 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.component.core import Component


class ProductProductExporter(Component):
    _name = 'product.product.exporter'
    _inherit = ['base.exporter']
    _apply_on = ['product.product']
    _usage = 'record.exporter'

    def update(self, binding, mode):
        vals = {
            'name': binding.name,
            'code': binding.default_code,
            'odoo_id': binding.id,
            'categ_id': binding.categ_id.id,
            'pvi_1': binding.get_product_price_with_pricelist('PVIA'),
            'pvi_2': binding.get_product_price_with_pricelist('PVIB'),
            'pvi_3': binding.get_product_price_with_pricelist('PVIC'),
            'pvi_4': binding.get_product_price_with_pricelist('PVID'),
            'pvi_5': binding.get_product_price_with_pricelist('PVIE'),
            'uom_name': binding.uom_id.name,
            'last_sixty_days_sales': binding.last_sixty_days_sales,
            'brand_id': binding.product_brand_id.id,
            'pvd_1': binding.get_product_price_with_pricelist('PVDA'),
            'pvd_2': binding.get_product_price_with_pricelist('PVDB'),
            'pvd_3': binding.get_product_price_with_pricelist('PVDC'),
            'pvd_4': binding.get_product_price_with_pricelist('PVDD'),
            'pvd_5': binding.get_product_price_with_pricelist('PVDE'),
            'pvm_1': binding.get_product_price_with_pricelist('PVMA'),
            'pvm_2': binding.get_product_price_with_pricelist('PVMB'),
            'pvm_3': binding.get_product_price_with_pricelist('PVMC'),
            'joking_index': binding.joking_index,
            'sale_ok': binding.sale_ok,
            'ean13': binding.barcode,
            'manufacturer_ref': binding.manufacturer_pref,
            'description_sale': binding.description_sale,
            'type': binding.type,
            'is_pack': binding.is_pack,
            'discontinued': binding.discontinued,
            'state': binding.state,
            'sale_in_groups_of': binding.sale_in_groups_of,
            'replacement_id': binding.replacement_id.id,
            'date_next_incoming': binding.compute_date_next_incoming(),
            'weight': binding.weight,
            'volume': binding.volume,
            'cost_price': binding.standard_price_2_inc,
            'real_stock': binding.qty_available
        }
        if binding.show_stock_outside:
            stock_qty = eval(
                "product." + self.backend_record.product_stock_field_id.name,
                {'product': binding})
            vals["stock"] = stock_qty
        if mode == "insert":
            self.backend_adapter.insert(vals)
        else:
            self.backend_adapter.update(binding.id, vals)
        return True

    def delete(self, binding):
        self.backend_adapter.remove(binding.id)
        return True

    def insert_product_tag_rel(self, product_record, tag_record):
        vals = {
            "odoo_id": product_record.id,
            "producttag_id": tag_record.id,
        }
        return self.backend_adapter.insert_rel('producttagproductrel', vals)

    def delete_product_tag_rel(self, partner_record_id):
        return self.backend_adapter.remove_rel(
            'producttagproductrel', partner_record_id)


class ProductProductAdapter(Component):

    _name = 'product.general.adapter'
    _inherit = 'middleware.adapter'
    _apply_on = 'product.product'
    _middleware_model = 'product'


class ProductCategoryExporter(Component):
    _name = 'product.category.exporter'
    _inherit = ['base.exporter']
    _apply_on = ['product.category']
    _usage = 'record.exporter'

    def update(self, binding, mode):
        vals = {"name": binding.with_context({'lang': 'es_ES'}).name,
                "parent_id": binding.parent_id.id,
                "odoo_id": binding.id
                }
        if mode == "insert":
            return self.backend_adapter.insert(vals)
        else:
            return self.backend_adapter.update(binding.id, vals)

    def delete(self, binding):
        return self.backend_adapter.remove(binding.id)


class ProductCategoryAdapter(Component):

    _name = 'productcategory.general.adapter'
    _inherit = 'middleware.adapter'
    _apply_on = 'product.category'
    _middleware_model = 'productcategory'


class ProductBrandExporter(Component):
    _name = 'product.brand.exporter'
    _inherit = ['base.exporter']
    _apply_on = ['product.brand']
    _usage = 'record.exporter'

    def update(self, binding, mode):
        vals = {"name": binding.name,
                "odoo_id": binding.id}
        if mode == "insert":
            return self.backend_adapter.insert(vals)
        else:
            return self.backend_adapter.update(binding.id, vals)

    def delete(self, binding):
        return self.backend_adapter.remove(binding.id)


class ProductBrandAdapter(Component):

    _name = 'productbrand.general.adapter'
    _inherit = 'middleware.adapter'
    _apply_on = 'product.brand'
    _middleware_model = 'productbrand'


class ProductbrandRelExporter(Component):
    _name = 'brand.country.rel.exporter'
    _inherit = ['base.exporter']
    _apply_on = ['brand.country.rel']
    _usage = 'record.exporter'

    def update(self, binding, mode):
        vals = {
            "country_id": binding.country_id.id,
            "brand_id": binding.brand_id.id,
            "odoo_id": binding.id
        }
        if mode == "insert":
            return self.backend_adapter.insert(vals)
        else:
            return self.backend_adapter.update(binding.id, vals)

    def delete(self, binding):
        return self.backend_adapter.remove(binding.id)


class ProductbrandRelAdapter(Component):

    _name = 'productbrandcountryrel.general.adapter'
    _inherit = 'middleware.adapter'
    _apply_on = 'brand.country.rel'
    _middleware_model = 'productbrandcountryrel'


class ProductTagExporter(Component):
    _name = 'product.tag.exporter'
    _inherit = ['base.exporter']
    _apply_on = ['product.tag']
    _usage = 'record.exporter'

    def update(self, binding, mode):
        vals = {
            "odoo_id": binding.id,
            "name": binding.name,
        }
        if mode == "insert":
            return self.backend_adapter.insert(vals)
        else:
            return self.backend_adapter.update(binding.id, vals)

    def delete(self, binding):
        return self.backend_adapter.remove(binding.id)


class ProductTagAdapter(Component):

    _name = 'producttag.general.adapter'
    _inherit = 'middleware.adapter'
    _apply_on = 'product.tag'
    _middleware_model = 'producttag'
