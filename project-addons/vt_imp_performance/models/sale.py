from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = "sale.order"

    name = fields.Char(index=False)
    create_date = fields.Datetime(index=False)
