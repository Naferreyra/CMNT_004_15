from odoo import models, fields


class ResCompany(models.Model):

    _inherit = "res.company"

    ean = fields.Char('EDI EAN')
