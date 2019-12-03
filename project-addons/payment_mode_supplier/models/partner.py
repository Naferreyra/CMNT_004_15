from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'
    payment_mode_suppliers = fields.Many2one('payment.mode.supplier', 'Suppliers Payment Mode')