from odoo import models, fields


class SaleOrderLine(models.Model):

    _inherit = 'sale.order.line'

    no_rappel = fields.Boolean(states={'draft': [('readonly', False)], 'reserve': [('readonly', False)]})
