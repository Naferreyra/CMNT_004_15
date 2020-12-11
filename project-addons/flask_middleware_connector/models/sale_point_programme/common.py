from odoo.addons.component.core import Component
from odoo.addons.queue_job.job import job
from odoo import api, fields, models


class SalePointProgrammeRuleListener(Component):
    _name = 'sale.point.programme.rule.event.listener'
    _inherit = 'base.event.listener'
    _apply_on = ['sale.point.programme.rule']

    def on_record_create(self, record, fields=None):
        record.with_delay(priority=1, eta=60).export_rule()

    def on_record_write(self, record, fields=None):
        up_fields = ["name","points","value","product_category_id","product_brand_id","product_id","operator","date_end"]
        for field in up_fields:
            if field in fields:
                record.with_delay(priority=2, eta=120).update_rule(fields=fields)

    def on_record_unlink(self, record):
        record.with_delay(priority=3, eta=120).unlink_rule()


class SalePointProgrammeRule(models.Model):
    _inherit = 'sale.point.programme.rule'

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def export_rule(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.update(self, 'insert')
        return True

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def update_rule(self, fields):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.update(self, 'update')
        return True

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def unlink_rule(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.delete(self)
        return True


class ResPartnerPointProgrammeBagAccumulatedListener(Component):
    _name = 'res.partner.point.programme.bag.accumulated.event.listener'
    _inherit = 'base.event.listener'
    _apply_on = ['res.partner.point.programme.bag.accumulated']

    def on_record_create(self, record, fields=None):
        if record.partner_id.commercial_partner_id.web:
            record.with_delay(priority=1, eta=60).export_point_programme_bag_acc()

    def on_record_write(self, record, fields=None):
        if record.partner_id.commercial_partner_id.web:
            record.with_delay(priority=2, eta=120).update_point_programme_bag_acc(fields=fields)

    def on_record_unlink(self, record):
        if record.partner_id.commercial_partner_id.web:
            record.with_delay(priority=3, eta=120).unlink_point_programme_bag_acc()


class ResPartnerPointProgrammeBagAccumulated(models.Model):
    _inherit = 'res.partner.point.programme.bag.accumulated'

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def export_point_programme_bag_acc(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.update(self, 'insert')
        return True

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def update_point_programme_bag_acc(self, fields):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.update(self, 'update')
        return True

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def unlink_point_programme_bag_acc(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.delete(self)
        return True
