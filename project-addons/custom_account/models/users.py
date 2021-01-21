
from odoo import models, api


class ResUsers(models.Model):

    _inherit = 'res.users'

    @api.model
    def create(self, vals):
        res = super(ResUsers, self).create(vals)
        if res.partner_id:
            employee_category_id = self.env.ref('custom_account.employee_category').id
            res.partner_id.category_id = [(4,employee_category_id)]
        return res

