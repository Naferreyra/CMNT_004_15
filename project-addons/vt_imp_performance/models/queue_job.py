from odoo import models, api, fields


class QueueJob(models.Model):
    _inherit = 'queue.job'

    company_id = fields.Many2one(index=False)
    channel = fields.Char(index=False)

    @api.model
    def create(self, values):
        """Se deshabilita la mensajería"""
        return super(QueueJob, self.
                     with_context({'tracking_disable': True})).create(values)

    @api.multi
    def write(self, values):
        """Se deshabilita la mensajería"""
        return super(QueueJob, self.
                     with_context({'tracking_disable': True})).write(values)
