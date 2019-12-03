from odoo import models, fields

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    payment_mode_suppliers = fields.Many2one(related="partner_id.payment_mode_suppliers")