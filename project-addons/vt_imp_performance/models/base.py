from odoo import models, fields


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    checksum = fields.Char(index=False)
    url = fields.Char(index=False)


class Property(models.Model):
    _inherit = 'ir.property'

    name = fields.Char(index=False)
    type = fields.Selection(index=False)


class IrTranslation(models.Model):
    _inherit = "ir.translation"

    comments = fields.Text(index=False)


class Partner(models.Model):
    _inherit = "res.partner"

    company_id = fields.Many2one(index=False)
    date = fields.Date(index=False)
