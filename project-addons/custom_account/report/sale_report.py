# Copyright 2019 Omar Castiñeira, Comunitea Servicios Tecnológicos S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class SaleReport(models.Model):
    _inherit = 'sale.report'

    brand_id = fields.Many2one('product.brand', 'Brand')
    parent_category_id = fields.Many2one("product.category", 'Parent categ.')
    partner_ref = fields.Char("Partner ref")
    state_name = fields.Char("State Name")
    main_supplier = fields.Many2one('res.partner', 'Main supplier')
    partner_vat = fields.Char("Partner VAT")
    partner_category = fields.Many2many(related='partner_id.category_id')
    partner_shipping_id = fields.Many2one('res.partner', string='Shipping Address')

    def _select(self):
        select_str = (", t.product_brand_id as brand_id, pc.parent_id as "
                      "parent_category_id, rp.ref as partner_ref, rp.vat as partner_vat , cs.name as "
                      "state_name, t.manufacturer as main_supplier, s.partner_shipping_id as partner_shipping_id")
        return super()._select() + select_str

    def _from(self):
        from_str = (" left join res_partner rp on s.partner_id=rp.id left join"
                    " product_category pc on pc.id = t.categ_id"
                    " LEFT JOIN res_country_state cs on cs.id = rp.state_id")
        return super()._from() + from_str

    def _group_by(self):
        group_by_str = """, t.product_brand_id, rp.ref, pc.parent_id, cs.name,
                          t.manufacturer, rp.vat, s.partner_shipping_id"""
        return super()._group_by() + group_by_str
