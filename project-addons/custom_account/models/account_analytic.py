
from odoo import models, fields, api, _, exceptions


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    ref = fields.Many2one('res.users')