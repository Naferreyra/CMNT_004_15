# © 2019 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models

from odoo.addons.component.core import Component
from odoo.addons.queue_job.job import job
from datetime import datetime


class PickingListener(Component):
    _name = 'picking.event.listener'
    _inherit = 'base.event.listener'
    _apply_on = ['stock.picking']

    def on_record_create(self, record, fields=None):
        picking = record
        if picking.partner_id.commercial_partner_id.web \
                and picking.partner_id.commercial_partner_id.active \
                and picking.picking_type_id.code == 'outgoing' \
                and not picking.not_sync \
                and picking.company_id.id == 1:
            picking.with_delay(priority=3, eta=30).export_picking()

    def on_record_write(self, record, fields=None):
        picking = record
        up_fields = ["date_done", "move_type", "carrier_name", "carrier_tracking_ref",
                     "state", "not_sync", "company_id", "partner_id"]
        model_name = 'stock.picking'
        if picking.partner_id.commercial_partner_id.web \
                and picking.partner_id.commercial_partner_id.active \
                and picking.picking_type_id.code == 'outgoing' \
                and not picking.not_sync \
                and picking.company_id.id == 1:
            if 'name' in fields or 'partner_id' in fields or ('not_sync' in fields and not picking.not_sync):
                picking.with_delay(priority=3, eta=30).export_picking()
                for product in picking.move_lines:
                    product.with_delay(priority=4, eta=60).export_pickingproduct()
            elif picking.state == 'cancel' \
                    or ('not_sync' in fields and picking.not_sync) \
                    or ('company_id' in fields and picking.company_id != 1):
                for product in picking.move_lines:
                    product.with_delay(priority=3, eta=30).unlink_pickingproduct()
                picking.with_delay(priority=4, eta=60).unlink_picking()
            else:
                if set(fields).intersection(set(up_fields)):
                    picking.with_delay(priority=3, eta=30).update_picking(fields=fields)
        else:
            job = self.env['queue.job'].sudo().search([('func_string', 'like', '%, ' + str(picking.id) + ')%'),
                                                       ('model_name', '=', model_name)], order='date_created desc',
                                                      limit=1)
            if job and 'unlink' not in job.name:
                record.with_delay(priority=4, eta=30).unlink_picking()

    def on_record_unlink(self, record):
        picking = record
        if picking.partner_id.commercial_partner_id.web \
                and picking.partner_id.commercial_partner_id.active \
                and picking.picking_type_id.code == 'outgoing' \
                and not picking.not_sync \
                and picking.company_id.id == 1:
            for product in picking.move_lines:
                product.with_delay(priority=3, eta=120).unlink_pickingproduct()
            record.with_delay(priority=4, eta=120).unlink_picking()


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def export_picking(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.update(self, 'insert')
        return True

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def update_picking(self, fields):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.update(self, 'update')
        return True

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def unlink_picking(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.delete(self)
        return True

    def button_validate(self):
        if self.claim_id:
            if self.picking_type_code == 'incoming':
                field = 'date_in'
            else:
                field = 'date_out'
            products = [x.product_id.id for x in self.move_lines]
            for claim_line in self.claim_id.claim_line_ids:
                if claim_line.product_id.id in products:
                    claim_line[field] = datetime.now()
        return super().button_validate()


class StockMoveListener(Component):
    _name = 'stock.move.event.listener'
    _inherit = 'base.event.listener'
    _apply_on = ['stock.move']

    def on_record_create(self, record, fields=None):
        for move_line in record:
            if move_line.picking_id.partner_id.commercial_partner_id.web \
                    and move_line.picking_id.partner_id.commercial_partner_id.active \
                    and move_line.picking_id.picking_type_id.code == 'outgoing' \
                    and not move_line.picking_id.not_sync \
                    and move_line.picking_id.company_id.id == 1:
                record.with_delay(priority=4, eta=60).export_pickingproduct()

    def on_record_write(self, record, fields=None):
        up_fields = ["parent_id", "product_uom_qty", "product_id", "picking_id"]
        for move_line in record:
            if move_line.picking_id.partner_id.commercial_partner_id.web \
                    and move_line.picking_id.partner_id.commercial_partner_id.active \
                    and move_line.picking_id.picking_type_id.code == 'outgoing'\
                    and not move_line.picking_id.not_sync \
                    and move_line.picking_id.company_id.id == 1:
                if 'picking_id' in fields:
                    record.with_delay(priority=4, eta=60).export_pickingproduct()
                if set(fields).intersection(set(up_fields)):
                    record.with_delay(priority=4, eta=120).update_pickingproduct(fields=fields)

    def on_record_unlink(self, record):
        for move_line in record:
            if move_line.picking_id.partner_id.commercial_partner_id.web \
                    and move_line.picking_id.partner_id.commercial_partner_id.active \
                    and move_line.picking_id.picking_type_id.code == 'outgoing' \
                    and not move_line.picking_id.not_sync \
                    and move_line.picking_id.company_id.id == 1:
                record.with_delay(priority=4, eta=120).unlink_pickingproduct()

    def on_stock_move_change(self, record):
        record._cr.execute("select 1 where '%s' in (select trim(trailing ']' from trim(leading '[' from record_ids)) "
                           "from queue_job where state = 'pending' and job_function_id = 486 and model_name = 'product.product')" % record.product_id.id)
        res = record._cr.fetchall()
        if record.product_id.show_stock_outside and not res:
            record.product_id.with_delay(priority=12, eta=30).update_product()
        packs = self.env['mrp.bom.line'].search([('product_id', '=', record.product_id.id)]).mapped('bom_id')
        for pack in packs:
            record._cr.execute("select 1 where '%s' in (select trim(trailing ']' from trim(leading '[' from record_ids)) "
                "from queue_job where state = 'pending' and job_function_id = 486 and model_name = 'product.product')" % pack.product_tmpl_id.product_variant_ids.id)
            if not record._cr.fetchall():
                pack.product_tmpl_id.product_variant_ids.with_delay(priority=12, eta=30).update_product()


class StockMove(models.Model):
    _inherit = 'stock.move'

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def export_pickingproduct(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.update(self, 'insert')
        return True

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def update_pickingproduct(self, fields):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.update(self, 'update')
        return True

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def unlink_pickingproduct(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.delete(self)
        return True

    # TODO: Debería ser al asignar un producto, al cancelarlo, al finalizarlo y al eliminar la reserve
    @api.multi
    def write(self, vals):
        res = super(StockMove, self).write(vals)
        picking_done = []
        for move in self:
            if vals.get('picking_id', False) or (vals.get('state', False) and move.picking_id):
                vals_picking = {}
                if vals.get('state', False):
                    vals_picking = {'state': vals['state']}
                else:
                    vals_picking = {'state': move.picking_id.state}
                if move.picking_id.id not in picking_done:
                    self._event('on_record_write').notify(self, fields=vals_picking.keys())
                    picking_done.append(move.picking_id.id)

            if vals.get('state', False) and vals["state"] != "draft":
                self._event('on_stock_move_change').notify(move)
        return res

