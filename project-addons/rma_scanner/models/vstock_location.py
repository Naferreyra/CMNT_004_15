from odoo import api, models, fields, _


class VstockLocation(models.Model):

    _name = 'vstock.location'

    vstock_id = fields.Char('Id', help='Physical Location')
    vstock_code = fields.Char('Code', help='Barcode')
