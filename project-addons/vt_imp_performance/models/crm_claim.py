from odoo import models, fields


class CrmClaim(models.Model):
    _inherit = "crm.claim"

    team_id = fields.Many2one(index=False)
