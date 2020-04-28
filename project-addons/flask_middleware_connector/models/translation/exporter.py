from odoo.addons.component.core import Component


class IrTranslationExporter(Component):
    _name = 'ir.translation.exporter'
    _inherit = ['base.exporter']
    _apply_on = ['ir.translation']
    _usage = 'record.exporter'

    def update(self, binding, mode):
        vals = {"model": binding.name.split(',')[0],
                "field": binding.name.split(',')[1],
                "res_id": binding.res_id,
                "lang": binding.lang,
                "source": binding.source,
                "value": binding.value,
                "odoo_id": binding.id}
        if mode == "insert":
            return self.backend_adapter.insert(vals)
        else:
            return self.backend_adapter.update(binding.id, vals)

    def delete(self, binding):
        return self.backend_adapter.remove(binding.id)


class IrTranslationAdapter(Component):

    _name = 'translation.general.adapter'
    _inherit = 'middleware.adapter'
    _apply_on = 'ir.translation'
    _middleware_model = 'translation'
