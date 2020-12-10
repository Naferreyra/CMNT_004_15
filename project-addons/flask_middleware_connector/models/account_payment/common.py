from odoo.addons.component.core import Component
from odoo.addons.queue_job.job import job
from odoo import api, fields, models


class PaymentLineListener(Component):
    _name = 'payment.line.listener'
    _inherit = 'base.event.listener'
    _apply_on = ['account.payment.line']

    def on_record_unlink(self, record):
        record.with_delay().unlink_payment_line()


class AccountPaymentOrder(models.Model):
    _inherit = 'account.payment.order'

    @api.multi
    def generated2uploaded(self):
        res = super(AccountPaymentOrder, self).generated2uploaded()
        for line in self.payment_line_ids:
            if line.payment_type == 'inbound' and line.partner_id.web:
                line.with_delay(priority=1).export_payment_line()
        return res


class AccountPaymentLine(models.Model):
    _inherit = 'account.payment.line'

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def export_payment_line(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.update(self, 'insert')

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def update_payment_line(self, fields):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.update(self, 'update')

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def unlink_payment_line(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.delete(self)
