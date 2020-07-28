from odoo.addons.component.core import Component
from odoo.addons.queue_job.job import job
from odoo import api, fields, models


class IrTranslationListener(Component):
    _name = 'ir.translation.listener'
    _inherit = 'base.event.listener'
    _apply_on = ['ir.translation']

    def on_record_create(self, record, fields=None):
        models = eval(self.env['ir.config_parameter'].sudo().get_param('translations.to.export'))
        # models looks like {'model1.name': ['field11', 'field12'], 'model2.name': ['field21']}
        name = record.name.split(',')
        # this should look like "model.name,field"
        if len(name) == 2:
            if name[0] in models.keys() and name[1] in models.get(name[0], []):
                record.with_delay(priority=1).export_translation()
                record.with_context({'no_update': True}).web = True

    def on_record_write(self, record, fields=None):
        models = eval(self.env['ir.config_parameter'].sudo().get_param('translations.to.export'))
        name = record.name.split(',')
        no_update = self.env.context.get('no_update',False)
        if not no_update and len(name) == 2:
            if name[0] in models.keys() and name[1] in models.get(name[0], []):
                if record.web:
                    record.with_delay(priority=2, eta=10).update_translation(fields=fields)
                else:
                    record.with_delay(priority=1).export_translation()
                    record.with_context({'no_update':True}).web = True

    def on_record_unlink(self, record):
        if len(record.name.split(',')) == 2 and record.web:
            record.with_delay().unlink_translation()
            record.with_context({'no_update':True}).web = False


class IrTranslation(models.Model):
    _inherit = 'ir.translation'

    web = fields.Boolean(default=False)

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def export_translation(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.update(self, 'insert')
        return True

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def update_translation(self, fields=None):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.update(self, 'update')
        return True

    @job(retry_pattern={1: 10 * 60, 2: 20 * 60, 3: 30 * 60, 4: 40 * 60, 5: 50 * 60})
    def unlink_translation(self):
        backend = self.env["middleware.backend"].search([])[0]
        with backend.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.delete(self)
        return True