from odoo.addons.component.core import Component

class SalePointProgrammeRuleExporter(Component):
    _name = 'sale.point.programme.rule.exporter'
    _inherit = ['base.exporter']
    _apply_on = ['sale.point.programme.rule']
    _usage = 'record.exporter'

    def update(self, binding, mode):
        vals = {
            "odoo_id": binding.id,
            "name": binding.name,
            "points": binding.points,
            "value": binding.value,
            "product_category_id": binding.category_id.id,
            "product_brand_id": binding.product_brand_id.id,
            "product_id": binding.product_id.id,
            "operator": binding.operator,
            "date_end": binding.date_end,
            "customertag_id": binding.partner_category_id.id
        }
        if mode == "insert":
            return self.backend_adapter.insert(vals)
        else:
            return self.backend_adapter.update(binding.id, vals)

    def delete(self, binding):
        return self.backend_adapter.remove(binding.id)


class SalePointProgrammeRuleAdapter(Component):

    _name = 'sale.point.programme.rule.adapter'
    _inherit = 'middleware.adapter'
    _apply_on = 'sale.point.programme.rule'
    _middleware_model = 'Customersalepointprogrammerule'

class ResPartnerPointProgrammeBagAccumulatedExporter(Component):
    _name = 'res.partner.point.programme.bag.accumulated.exporter'
    _inherit = ['base.exporter']
    _apply_on = ['res.partner.point.programme.bag.accumulated']
    _usage = 'record.exporter'

    def update(self, binding, mode):
        vals = {
            "odoo_id": binding.id,
            "name": binding.name,
            "points": binding.points,
            "point_rule_id": binding.point_rule_id.id,
            "partner_id": binding.partner_id.id,
        }
        if mode == "insert":
            return self.backend_adapter.insert(vals)
        else:
            return self.backend_adapter.update(binding.id, vals)

    def delete(self, binding):
        return self.backend_adapter.remove(binding.id)


class ResPartnerPointProgrammeBagAccumulatedAdapter(Component):

    _name = 'res.partner.point.programme.bag.accumulated.adapter'
    _inherit = 'middleware.adapter'
    _apply_on = 'res.partner.point.programme.bag.accumulated'
    _middleware_model = 'Customersalepointprogramme'
