from odoo import models, fields


#  used in fatturaPa export
class AccountPaymentMode(models.Model):
    # _position = ['2.4.2.2']
    _inherit = 'account.payment.mode'

    fatturapa_pm_id = fields.Many2one(
        'fatturapa.payment_method', string="Fiscal Payment Method")
