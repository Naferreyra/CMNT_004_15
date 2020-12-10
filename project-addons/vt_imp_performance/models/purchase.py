from odoo import models, fields


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    name = fields.Char(index=False)


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    date_planned = fields.Datetime(index=False)
