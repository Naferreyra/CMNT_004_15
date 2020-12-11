from odoo import models, fields


class CrmPhonecall(models.Model):
    _inherit = "crm.phonecall"

    team_id = fields.Many2one(index=True)


class MergeOpportunity(models.TransientModel):
    _inherit = 'crm.merge.opportunity'

    user_id = fields.Many2one(index=False)
    team_id = fields.Many2one(index=False)


class Lead2OpportunityPartner(models.TransientModel):

    _inherit = 'crm.lead2opportunity.partner'

    user_id = fields.Many2one(index=True)
    team_id = fields.Many2one(index=True)
