# © 2019 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.component.core import Component
import base64


class StockPickingExporter(Component):
    _name = 'stock.picking.exporter'
    _inherit = ['base.exporter']
    _apply_on = ['stock.picking']
    _usage = 'record.exporter'

    def update(self, binding, mode):
        name = binding.name.replace("\\", "/")
        vals = {
                "odoo_id": binding.id,
                "name": name,
                "partner_id": binding.partner_id.commercial_partner_id.id,
                "date": binding.date,
                "date_done": binding.date_done or "",
                "move_type": binding.move_type,
                "carrier_name": binding.carrier_name or "",
                "carrier_tracking_ref": binding.carrier_tracking_ref or "",
                "origin": binding.origin,
                "state": binding.state,
                "pdf_file_data": "",
                "dropship": binding.partner_id.dropship,
                }
        if mode == "insert":
            return self.backend_adapter.insert(vals)
        else:
            return self.backend_adapter.update(binding.id, vals)

    def delete(self, binding):
        return self.backend_adapter.remove(binding.id)


class StockPickingAdapter(Component):

    _name = 'picking.general.adapter'
    _inherit = 'middleware.adapter'
    _apply_on = 'stock.picking'
    _middleware_model = 'picking'


class StockMoveExporter(Component):
    _name = 'stock.move.exporter'
    _inherit = ['base.exporter']
    _apply_on = ['stock.move']
    _usage = 'record.exporter'

    def update(self, binding, mode):
        vals = {
            "odoo_id": binding.id,
            "product_id": binding.product_id.id,
            "product_qty": binding.product_uom_qty,
            "picking_id": binding.picking_id.id
        }

        if mode == "insert":
            return self.backend_adapter.insert(vals)
        else:
            return self.backend_adapter.update(binding.id, vals)

    def delete(self, binding):
        return self.backend_adapter.remove(binding.id)


class StockMoveAdapter(Component):

    _name = 'pickingproduct.general.adapter'
    _inherit = 'middleware.adapter'
    _apply_on = 'stock.move'
    _middleware_model = 'pickingproduct'
