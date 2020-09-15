from odoo import models, fields, _, exceptions, api


class KitchenCustomization(models.Model):
    _name = 'customization.type'

    name = fields.Char('Name')
