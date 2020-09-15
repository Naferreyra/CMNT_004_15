# © 2019 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.component.core import Component
from odoo.addons.queue_job.job import job
from odoo import api, fields, models
import datetime


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    web = fields.Selection([('not_published', 'Not published'),
                            ('published', 'Published')], "Web",
                           default="not_published", copy=False,
                           help="Allow to publish product description "
                                "in public web service")
    show_stock_outside = fields.Boolean("Show stock outside", copy=False,
                                        help="Allow to publish stock info "
                                             "in public web service",
                                        default=True)

    def write(self, vals):
        delete = True
        if vals.get('web', False):
            for record in self:
                if record.web != vals['web']:
                    delete = False
                    break
            if delete:
                del vals['web']

        if vals.get('description_sale', False):
            description_sale = vals['description_sale']
            if description_sale[-1] == '\n':
                description_sale = description_sale[0:(len(description_sale) - 2)]
                vals['description_sale'] = description_sale

        return super().write(vals)


class ProductTemplateListener(Component):
    _name = 'product.template.event.listener'
    _inherit = 'base.event.listener'
    _apply_on = ['product.template']

    def on_record_write(self, record, fields=None):
        up_fields = [
            "name", "list_price", "categ_id", "product_brand_id",
            "show_stock_outside", "sale_ok", "weight", "volume"]
        if record.image or len(fields) != 1:
            for field in up_fields:
                if field in fields:
                    product = self.env["product.product"].search(
                        [('product_tmpl_id', '=', record.id)])
                    product.with_delay(priority=3, eta=60).update_product()
                    break


class ProductListener(Component):
    _name = 'product.event.listener'
    _inherit = 'base.event.listener'
    _apply_on = ['product.product']

    def on_record_create(self, record, fields=None):
        record.with_delay().export_product()
        claim_lines = self.env['claim.line'].search(
            [('product_id', '=', record.id),
             ('claim_id.partner_id.web', '=', True)])
        for line in claim_lines:
            if not line.equivalent_product_id:
                line.with_delay(priority=10, eta=120).export_rmaproduct()
        claim_lines = self.env['claim.line'].search(
            [('equivalent_product_id', '=', record.id),
             ('claim_id.partner_id.web', '=', True)])
        for line in claim_lines:
            line.with_delay(priority=10, eta=120).export_rmaproduct()

    def on_record_write(self, record, fields=None):
        up_fields = [
            "default_code", "pvi1_price", "pvi2_price", "pvi3_price",
            "pvi4_price", "list_price2", "list_price3", "list_price4",
            "pvd1_relation", "pvd2_relation", "pvd3_relation", "pvd4_relation",
            "last_sixty_days_sales", "joking_index", "sale_ok", "barcode",
            "description_sale", "manufacturer_pref", "standard_price", "type",
            "discontinued", "state", "item_ids", "sale_in_groups_of", "replacement_id",
            "weight", "volume", "standard_price_2_inc"
        ]
        for field in up_fields:
            if field in fields:
                record.with_delay(priority=2, eta=30).update_product()
                break

        packs = self.env['mrp.bom.line'].search([('product_id', '=', record.id)]).mapped('bom_id')
        for pack in packs:
            min_stock = False
            for line in pack.bom_line_ids:
                product_stock_qty = line.product_id.virtual_available_wo_incoming
                if not min_stock or min_stock > product_stock_qty:
                    min_stock = product_stock_qty
            if min_stock:
                pack.product_tmpl_id.product_variant_ids.with_delay(priority=2, eta=30).update_product()

        if 'tag_ids' in fields:
            record.with_delay(priority=1, eta=30).unlink_product_tag_rel()
            record.with_delay(priority=2, eta=60).export_product_tag_rel()

    def on_record_unlink(self, record):
        record.with_delay().unlink_product()


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.depends('bom_ids','bom_ids.type','bom_ids.bom_line_ids')
    def _compute_is_pack(self):
        for product in self:
            if product.bom_ids.filtered(lambda r: r.type == 'phantom'):
                product.is_pack = True
            else:
                product.is_pack = False

    is_pack = fields.Boolean(compute='_compute_is_pack', store=True)

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def export_product(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.update(self, 'insert')
        return True

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def update_product(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.update(self, 'update')
        return True

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def unlink_product(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.delete(self)
        return True


    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def export_product_tag_rel(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            for tag in self.tag_ids:
                exporter.insert_product_tag_rel(self, tag)
        return True

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def unlink_product_tag_rel(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.delete_product_tag_rel(self)
        return True

    def compute_date_next_incoming(self):
        moves = self.env['stock.move'].search(
            [('product_id', '=', self.id), ('purchase_line_id', '!=', False), ('state', 'not in', ['cancel','done']),
             ('location_dest_id.usage', 'like', 'internal'),'|',('picking_id','!=',False),('container_id','!=',False)]).sorted(
            key=lambda m: m.date_expected and m.date_reliability)
        if moves:
            return moves[0].date_expected
        return (datetime.datetime.now() - datetime.timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")


class ProductCategoryListener(Component):
    _name = 'product.category.event.listener'
    _inherit = 'base.event.listener'
    _apply_on = ['product.category']

    def on_record_create(self, record, fields=None):
        record.with_delay(priority=1).export_product_category()

    def on_record_write(self, record, fields=None):
        up_fields = ["name", "parent_id"]
        for field in up_fields:
            if field in fields:
                record.with_delay().update_product_category()
                break

    def on_record_unlink(self, record):
        record.with_delay().unlink_product_category()


class ProductCategory(models.Model):
    _inherit = 'product.category'

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def export_product_category(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.update(self, 'insert')
        return True

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def update_product_category(self, fields=None):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.update(self, 'update')
        return True

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def unlink_product_category(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.delete(self)
        return True


class ProductBrandListener(Component):
    _name = 'product.brand.event.listener'
    _inherit = 'base.event.listener'
    _apply_on = ['product.brand']

    def on_record_create(self, record, fields=None):
        record.with_delay(priority=0).export_product_brand()

    def on_record_write(self, record, fields=None):
        up_fields = ["name"]
        for field in up_fields:
            if field in fields:
                record.with_delay().update_product_brand(fields)
                break

    def on_record_unlink(self, record):
        record.with_delay().unlink_product_brand()


class ProductBrand(models.Model):
    _inherit = 'product.brand'

    country_ids = fields.One2many('brand.country.rel', 'brand_id', 'Countries')

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def export_product_brand(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.update(self, 'insert')
        return True

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def update_product_brand(self, fields):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.update(self, 'update')
        return True

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def unlink_product_brand(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.delete(self)
        return True


class BrandCountryRel(models.Model):

    _name = 'brand.country.rel'

    brand_id = fields.Many2one('product.brand', 'Brand')
    country_id = fields.Many2one('res.country', 'Country')


class BrandCountryListener(Component):
    _name = 'brand.country.event.listener'
    _inherit = 'base.event.listener'
    _apply_on = ['brand.country.rel']

    def on_record_create(self, record, fields=None):
        record.with_delay(priority=50).export_product_brand_rel()

    def on_record_write(self, record, fields=None):
        up_fields = ["brand_id", "country_id"]
        for field in up_fields:
            if field in fields:
                record.with_delay(delay=50).update_product_brand_rel()
                break

    def on_record_unlink(self, record):
        record.with_delay(priority=1).unlink_product_brand_rel()


class BrandCountryRel(models.Model):
    _inherit = 'brand.country.rel'

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def export_product_brand_rel(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.update(self, 'insert')
        return True

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def update_product_brand_rel(self, fields):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.update(self, 'update')
        return True

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def unlink_product_brand_rel(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.delete(self)
        return True


class ProductTagsListener(Component):
    _name = 'product.tag.event.listener'
    _inherit = 'base.event.listener'
    _apply_on = ['product.tag']

    def on_record_create(self, record, fields=None):
        record.with_delay(priority=1, eta=60).export_product_tag()
        if 'product_ids' in fields:
            for product in record.product_ids:
                product.with_delay(priority=1, eta=30).unlink_product_tag_rel()
                product.with_delay(priority=2, eta=60).export_product_tag_rel()

    def on_record_write(self, record, fields=None):
        record.with_delay(priority=2, eta=120).update_product_tag()
        if 'product_ids' in fields:
            for product in record.product_ids:
                product.with_delay(priority=1, eta=30).unlink_product_tag_rel()
                product.with_delay(priority=2, eta=60).export_product_tag_rel()

    def on_record_unlink(self, record):
        record.with_delay(priority=3, eta=120).unlink_product_tag()


class ProductTag(models.Model):
    _inherit = 'product.tag'

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def export_product_tag(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.update(self, 'insert')
        return True

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def update_product_tag(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.update(self, 'update')
        return True

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def unlink_product_tag(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.delete(self)
        return True
