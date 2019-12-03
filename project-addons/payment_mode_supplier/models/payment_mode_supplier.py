from odoo import models, fields

class PaymentModeSuppliers(models.Model):
    _name = 'payment.mode.supplier'

    name = fields.Char(required=True,String="Name")