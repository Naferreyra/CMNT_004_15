# © 2019 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields, api, _


class MiddlewareBackend(models.TransientModel):
    _name = 'middleware.backend.export'

    type_export = fields.Selection(
        selection=[
            ('partner', 'Partner'),
            ('users', 'User'),
            ('invoices', 'Invoices'),
            ('pickings', 'Pickings'),
            ('rma', 'RMAs'),
            ('products', 'Products'),
            ('order', 'Orders'),
            ('tags', 'Tags'),
            ('customer_tags_rel', 'Customer Tags Rel'),
            ('translation', 'Translations'),
            ('rappel', 'Rappel'),
            ('rappel_section', 'Rappel Sections'),
            ('rappel_info', 'Rappel info'),
            ('country', 'Country'),
            ('country_state', 'States'),
            ('product_tag', 'Product Tag'),
            ('product_tag_product_rel', 'Product Tags Rel'),
            ('product_brand', 'Product Brand'),
            ('product_brand_product_rel', 'Product Brand Rel'),
            ('product_category', 'Product Category')
        ],
        string='Export type',
        required=True,
    )

    mode_export = fields.Selection(
        selection=[
            ('export', 'Export'),
            ('update', 'Update'),
            ('unlink', 'Unlink')
        ],
        string='Export mode',
        required=True,
    )

    start_date = fields.Date('Start Date',
                             default=fields.Date.context_today)
    finish_date = fields.Date('Finish Date',
                              default=fields.Date.context_today)
    model_ids = fields.Char('Ids')

    model_names = fields.Char('Translations names',
                              help='In this field, you have to write the list of model names to export its translation with one of these formats:  "model.name:[id1,id2];model.name2:[id1,id2]" or "model.name:[];model.name2:[]" or "model.name;model.name2"')

    @api.multi
    def do_export(self):
        if self.model_ids:
            object_ids = list(map(int, self.model_ids.split(',')))
        else:
            object_ids = False
        switcher={
            'partner': self.export_partner,
            'invoices': self.export_invoices,
            'pickings': self.export_pickings,
            'rma': self.export_rmas,
            'products': self.export_products,
            'tags': self.export_tags,
            'customer_tags_rel': self.export_customer_tags_rel,
            'order': self.export_orders,
            'rappel': self.export_rappel,
            'rappel_section': self.export_rappels_section,
            'country_state': self.export_country_states,
            'product_tag': self.export_product_tags,
            'product_tag_product_rel': self.export_product_tag_product_rel,
            'users': self.export_users,
            'translation': self.export_translations,
            'rappel_info': self.export_rappel_info,
            'country': self.export_countries,
            'product_brand': self.export_product_brand,
            'product_brand_product_rel': self.export_product_brand_product_rel,
            'product_category': self.export_product_category
        }
        switcher.get(self.type_export)(object_ids)

    def export_partner(self, object_ids):
        partner_obj = self.env['res.partner']
        if object_ids:
            partner_ids = partner_obj.browse(object_ids)
        else:
            partner_ids = partner_obj.search([('is_company', '=', True),
                                              ('web', '=', True),
                                              ('customer', '=', True)])
        contact_ids = partner_obj.search([('id', 'child_of', partner_ids.ids),
                                          ('id', 'not in', partner_ids.ids),
                                          ('customer', '=', True),
                                          ('is_company', '=', False)])
        if self.mode_export == 'export':
            for partner in partner_ids:
                # Export all the partner things
                partner.with_delay().export_partner()
                partner.with_delay(eta=10).export_partner_tag_rel()
                sales = self.env['sale.order'].search(
                    [('partner_id', 'child_of', [partner.id]),
                     ('company_id', '=', 1),
                     ('state', 'in', ['done', 'sale'])])
                for sale in sales:
                    sale.with_delay(priority=5, eta=120).export_order()
                    for line in sale.order_line:
                        line.with_delay(
                            priority=10, eta=180).export_orderproduct()
                invoices = self.env['account.invoice'].search(
                    [('commercial_partner_id', '=', partner.id),
                     ('company_id', '=', 1),
                     ('number', 'not like', '%ef%')])
                for invoice in invoices:
                    invoice.with_delay(priority=5, eta=120).export_invoice()
                rmas = self.env['crm.claim'].search(
                    [('partner_id', '=', partner.id)])
                for rma in rmas:
                    rma.with_delay(priority=5, eta=120).export_rma()
                    for line in rma.claim_line_ids:
                        if line.product_id.web == 'published' and \
                                (not line.equivalent_product_id or
                                 line.equivalent_product_id.web ==
                                 'published'):
                            line.with_delay(
                                priority=10, eta=240).export_rmaproduct()
                pickings = self.env['stock.picking'].search([
                    ('partner_id', 'child_of', [partner.id]),
                    ('state', '!=', 'cancel'),
                    ('picking_type_id.code', '=', 'outgoing'),
                    ('company_id', '=', 1),
                    ('not_sync', '=', False)])
                for picking in pickings:
                    picking.with_delay(priority=5, eta=120).export_picking()
                    for line in picking.move_lines:
                        line.with_delay(
                            priority=10, eta=240).export_pickingproduct()
            for contact in contact_ids:
                contact.with_delay().export_partner()
        elif self.mode_export == 'update':
            for partner in partner_ids:
                partner.with_delay().update_partner()
            for contact in contact_ids:
                contact.with_delay().update_partner()
        else:
            for partner in partner_ids:
                partner.with_delay().unlink_partner()
            for contact in contact_ids:
                contact.with_delay().unlink_partner()

    def export_invoices(self, object_ids):
        if object_ids:
            invoices = self.env['account.invoice'].browse(object_ids)
        else:
            invoices = self.env['account.invoice']. \
                search([('commercial_partner_id.web', '=', True),
                        ('state', 'in', ['open', 'paid']),
                        ('number', 'not like', '%ef%'),
                        ('company_id', '=', 1),
                        ('date_invoice', '>=', self.start_date),
                        ('date_invoice', '<=', self.finish_date)])
        if self.mode_export == 'export':
            for invoice in invoices:
                invoice.with_delay().export_invoice()
        elif self.mode_export == 'update':
            for invoice in invoices:
                invoice.with_delay().update_invoice(fields=None)
        else:
            for invoice in invoices:
                invoice.with_delay().unlink_invoice()

    def export_pickings(self, object_ids):
        if object_ids:
            picking_ids = self.env['stock.picking'].browse(object_ids)
        else:
            partner_obj = self.env['res.partner']
            partner_ids = partner_obj.search([('is_company', '=', True),
                                              ('web', '=', True),
                                              ('customer', '=', True)])
            picking_obj = self.env['stock.picking']
            picking_ids = picking_obj.search([('partner_id', 'child_of', partner_ids.ids),
                                              ('state', '!=', 'cancel'),
                                              ('company_id', '=', 1),
                                              ('not_sync', '=', False),
                                              ('date', '>=', self.start_date),
                                              ('date', '<=', self.finish_date),
                                              ('picking_type_id.code', '=', 'outgoing')])
        if self.mode_export == 'export':
            for picking in picking_ids:
                picking.with_delay().export_picking()
                for line in picking.move_lines:
                    line.with_delay().export_pickingproduct()

        elif self.mode_export == 'update':
            for picking in picking_ids:
                picking.with_delay().update_picking(fields=None)
                for line in picking.move_lines:
                    line.with_delay().update_pickingproduct(fields=None)
        else:
            for picking in picking_ids:
                picking.with_delay().unlink_picking()
                for line in picking.move_lines:
                    line.with_delay().unlink_pickingproduct()

    def export_rmas(self, object_ids):
        rma_obj = self.env['crm.claim']
        if object_ids:
            rmas = rma_obj.browse(object_ids)
        else:
            rmas = rma_obj.search(['|', ('partner_id.web', '=', True),
                                   ('partner_id.commercial_partner_id.web', '=', True),
                                   ('date', '>=', self.start_date),
                                   ('date', '<=', self.finish_date)])
        if self.mode_export == 'export':
            for rma in rmas:
                rma.with_delay().export_rma()
                for line in rma.claim_line_ids:
                    line.with_delay().export_rmaproduct()
        elif self.mode_export == 'update':
            for rma in rmas:
                rma.with_delay().update_rma()
                for line in rma.claim_line_ids:
                    line.with_delay().update_rmaproduct(fields=None)
        else:
            for rma in rmas:
                rma.with_delay().unlink_rma()
                for line in rma.claim_line_ids:
                    line.with_delay().unlink_rmaproduct()

    def export_products(self, object_ids):
        product_obj = self.env['product.product']
        if object_ids:
            product_ids = product_obj.browse(object_ids)
        else:
            product_ids = product_obj.search([])
        if self.mode_export == 'export':
            for product in product_ids:
                product.with_delay().export_product()
                product.with_delay(priority=1, eta=30).unlink_product_tag_rel()
                product.with_delay(priority=2, eta=60).export_product_tag_rel()
        elif self.mode_export == 'update':
            for product in product_ids:
                product.with_delay().update_product()
                product.with_delay(priority=1, eta=30).unlink_product_tag_rel()
                product.with_delay(priority=2, eta=60).export_product_tag_rel()
        else:
            for product in product_ids:
                product.with_delay().unlink_product()
                product.with_delay(priority=1, eta=60).unlink_product_tag_rel()

    def export_tags(self, object_ids):
        tag_obj = self.env['res.partner.category']
        if object_ids:
            tag_ids = tag_obj.browse(object_ids)
        else:
            tag_ids = tag_obj.search([('active', '=', True)])
        if self.mode_export == 'export':
            for tag in tag_ids:
                tag.with_delay(priority=5).export_partner_tag()
                for partner in tag.partner_ids:
                    partner.with_delay(priority=1).unlink_partner_tag_rel()
                    partner.with_delay(priority=2, eta=10).export_partner_tag_rel()
        elif self.mode_export == 'update':
            for tag in tag_ids:
                tag.with_delay(priority=5).update_partner_tag()
                for partner in tag.partner_ids:
                    partner.with_delay(priority=1).unlink_partner_tag_rel()
                    partner.with_delay(priority=2, eta=10).export_partner_tag_rel()
        else:
            for tag in tag_ids:
                tag.with_delay().unlink_partner_tag()

    def export_customer_tags_rel(self, object_ids):
        partner_obj = self.env['res.partner']
        if object_ids:
            partner_ids = partner_obj.browse(object_ids)
        else:
            partner_ids = partner_obj.search([('is_company', '=', True),
                                              ('web', '=', True),
                                              ('customer', '=', True)])
        if self.mode_export in ('export','update'):
            for partner in partner_ids:
                partner.with_delay(priority=1).unlink_partner_tag_rel()
                partner.with_delay(priority=2, eta=10).export_partner_tag_rel()
        else:
            for partner in partner_ids:
                partner.with_delay().unlink_partner_tag_rel()

    def export_orders(self, object_ids):
        if object_ids:
            sales = self.env['sale.order'].browse(object_ids)
        else:
            partner_obj = self.env['res.partner']
            partner_ids = partner_obj.search([('is_company', '=', True),
                                              ('web', '=', True),
                                              ('customer', '=', True)])
            sales = self.env['sale.order'].search([('partner_id', 'child_of', partner_ids.ids),
                                                   ('state', 'in', ['done', 'sale']),
                                                   ('date_order', '>=', self.start_date),
                                                   ('date_order', '<=', self.finish_date),
                                                   ('company_id', '=', 1)])
        if self.mode_export == 'export':
            for sale in sales:
                sale.with_delay(priority=5).export_order()
                for line in sale.order_line:
                    line.with_delay().export_orderproduct()
        elif self.mode_export == 'update':
            for sale in sales:
                sale.with_delay(priority=5).update_order(fields=None)
                for line in sale.order_line:
                    line.with_delay().update_orderproduct(fields=None)
        else:
            for sale in sales:
                sale.with_delay().unlink_order()
                for line in sale.order_line:
                    line.with_delay().unlink_orderproduct()

    def export_rappel(self, object_ids):
        rappel_obj = self.env['rappel']
        if object_ids:
            rappel_ids = rappel_obj.browse(object_ids)
        else:
            rappel_ids = rappel_obj.search([])
        if self.mode_export == 'export':
            for rappel in rappel_ids:
                rappel.with_delay().export_rappel()
        elif self.mode_export == 'update':
            for rappel in rappel_ids:
                rappel.with_delay().update_rappel(fields=None)
        else:
            for rappel in rappel_ids:
                rappel.with_delay().unlink_rappel()

    def export_rappels_section(self, object_ids):
        rappel_section_obj = self.env['rappel.section']
        if object_ids:
            rappel_section_ids = rappel_section_obj.browse(object_ids)
        else:
            rappel_section_ids = rappel_section_obj.search([])
        if self.mode_export == 'export':
            for section in rappel_section_ids:
                section.with_delay().export_rappel_section()
        elif self.mode_export == 'update':
            for section in rappel_section_ids:
                section.with_delay().update_rappel_section(fields=None)
        else:
            for section in rappel_section_ids:
                section.with_delay().unlink_rappel_section()

    def export_country_states(self, object_ids):
        country_state_obj = self.env['res.country.state']
        if object_ids:
            country_state_ids = country_state_obj.browse(object_ids)
        else:
            country_state_ids = country_state_obj.search([])
        if self.mode_export == 'export':
            for section in country_state_ids:
                section.with_delay().export_country_state()
        elif self.mode_export == 'update':
            for section in country_state_ids:
                section.with_delay().update_country_state(fields=None)
        else:
            for section in country_state_ids:
                section.with_delay().unlink_country_state()

    def export_product_tags(self, object_ids):
        product_tag_obj = self.env['product.tag']
        if object_ids:
            product_tag_ids = product_tag_obj.browse(object_ids)
        else:
            product_tag_ids = product_tag_obj.search([])
        if self.mode_export == 'export':
            for tag in product_tag_ids:
                tag.with_delay().export_product_tag()
                for product in tag.product_ids:
                    product.with_delay(priority=1, eta=30).unlink_product_tag_rel()
                    product.with_delay(priority=2, eta=60).export_product_tag_rel()
        elif self.mode_export == 'update':
            for tag in product_tag_ids:
                tag.with_delay().update_product_tag(fields=None)
                for product in tag.product_ids:
                    product.with_delay(priority=1, eta=30).unlink_product_tag_rel()
                    product.with_delay(priority=2, eta=60).export_product_tag_rel()
        else:
            for tag in product_tag_ids:
                tag.with_delay().unlink_product_tag()

    def export_product_tag_product_rel(self, object_ids):
        product_obj = self.env['product.product']
        if object_ids:
            product_ids = product_obj.browse(object_ids)
        else:
            product_ids = product_obj.search([])

        if self.mode_export == 'export':
            for product in product_ids:
                product.with_delay(priority=1).unlink_product_tag_rel()
                product.with_delay(priority=2, eta=5).export_product_tag_rel()
        else:
            for product in product_ids:
                product.with_delay(priority=1).unlink_product_tag_rel()

    def export_users(self, object_ids):
        user_obj = self.env['res.users']
        if object_ids:
            user_ids = user_obj.browse(object_ids)
        else:
            user_ids = user_obj.search([])

        if self.mode_export == 'export':
            for user in user_ids:
                if user.web:
                    user.with_delay(priority=1).export_commercial()
        elif self.mode_export == 'update':
            for user in user_ids:
                if user.web:
                    user.with_delay(priority=3).update_commercial(fields=None)
        else:
            for user in user_ids:
                user.with_delay(priority=100).unlink_commercial()

    def export_rappel_info(self, object_ids):
        rappel_info_obj = self.env['rappel.current.info']
        if object_ids:
            rappel_info_ids = rappel_info_obj.browse(object_ids)
        else:
            rappel_info_ids = rappel_info_obj.search([])

        if self.mode_export == 'export':
            for rappel_info in rappel_info_ids:
                if rappel_info.partner_id.commercial_partner_id.web:
                    rappel_info.with_delay(priority=1, eta=60).export_rappel_info()
        elif self.mode_export == 'update':
            for rappel_info in rappel_info_ids:
                if rappel_info.partner_id.commercial_partner_id.web:
                    rappel_info.with_delay(priority=2, eta=120).update_rappel_info(fields=None)
        else:
            for rappel_info in rappel_info_ids:
                if rappel_info.partner_id.commercial_partner_id.web:
                    rappel_info.with_delay(priority=3, eta=120).unlink_rappel_info()

    def export_translations(self,_):
        translations_obj = self.env['ir.translation']

        models = eval(self.env['ir.config_parameter'].sudo().get_param('translations.to.export'))
        # models looks like {'model1.name': ['field11', 'field12'], 'model2.name': ['field21']}

        # translation_name should look like "model.name:[ids];model2.name:[];model2.name"
        self.model_names = self.model_names.replace(" ","")
        for translation_name in self.model_names.split(';'):
            name_with_ids = translation_name.split(':')
            # this should look like "model.name:[id1,id2]"
            model_name = '%' + name_with_ids[0] + '%'
            if len(name_with_ids) == 2:
                translations_ids = translations_obj.search(
                    [('res_id', 'in', eval(name_with_ids[1])), ('name', 'like', model_name)])
            else:
                translations_ids = translations_obj.search([('name', 'like', model_name)])

            for translation in translations_ids:
                name = translation.name.split(',')
                # this should look like "model.name,field"
                if len(name) == 2:
                    if self.mode_export in ('export','update'):
                        if name[0] in models.keys() and name[1] in models.get(name[0], []):
                            if translation.web:
                                translation.with_delay(priority=2, eta=10).update_translation()
                            else:
                                translation.with_delay(priority=1).export_translation()
                                translation.with_context({'no_update':True}).web = True
                    elif translation.web:
                        translation.with_delay().unlink_translation()
                        translation.with_context({'no_update':True}).web = False


    def export_countries(self,object_ids):
        res_country_obj = self.env['res.country']
        if object_ids:
            res_country_ids = res_country_obj.browse(object_ids)
        else:
            res_country_ids = res_country_obj.search([])
        if self.mode_export == 'export':
            for res_country in res_country_ids:
                res_country.with_delay(priority=1).export_country()
        elif self.mode_export == 'update':
            for res_country in res_country_ids:
                res_country.with_delay(priority=3).update_country(fields=None)
        else:
            for res_country in res_country_ids:
                res_country.with_delay(priority=100).unlink_country()

    def export_product_brand(self,object_ids):
        product_brand_obj = self.env['product.brand']
        if object_ids:
            product_brand_ids = product_brand_obj.browse(object_ids)
        else:
            product_brand_ids = product_brand_obj.search([])
        if self.mode_export == 'export':
            for product_brand in product_brand_ids:
                product_brand.with_delay().export_product_brand()
        elif self.mode_export == 'update':
            for product_brand in product_brand_ids:
                product_brand.with_delay().update_product_brand(fields=None)
        else:
            for product_brand in product_brand_ids:
                product_brand.with_delay().unlink_product_brand()

    def export_product_brand_product_rel(self,object_ids):
        brand_country_rel_obj = self.env['brand.country.rel']
        if object_ids:
            brand_country_rel_ids = brand_country_rel_obj.browse(object_ids)
        else:
            brand_country_rel_ids = brand_country_rel_obj.search([])
        if self.mode_export == 'export':
            for brand_country in brand_country_rel_ids:
                brand_country.with_delay(priority=50).export_product_brand_rel()
        elif self.mode_export == 'update':
            for brand_country in brand_country_rel_ids:
                brand_country.with_delay(delay=50).update_product_brand_rel()
        else:
            for brand_country in brand_country_rel_ids:
                brand_country.with_delay(priority=1).unlink_product_brand_rel()

    def export_product_category(self,object_ids):
        product_category_obj = self.env['product.category']
        if object_ids:
            product_category_ids = product_category_obj.browse(object_ids)
        else:
            product_category_ids = product_category_obj.search([])
        if self.mode_export == 'export':
            for product_category in product_category_ids:
                product_category.with_delay(priority=1).export_product_category()
        elif self.mode_export == 'update':
            for product_category in product_category_ids:
                product_category.with_delay().update_product_category()
        else:
            for product_category in product_category_ids:
                product_category.with_delay().unlink_product_category()