from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    warehouse_location = fields.Selection([('madrid1', 'Madrid - Avd. del Sol'),
                                           ('madrid2', 'Madrid - Casablanca'),
                                           ('italia', 'Italia - Arcore')], "Warehouse Location")
