
from odoo import models, fields, _, exceptions, api
from odoo.exceptions import except_orm, UserError


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    @api.model
    def create(self, vals):
        res = super(StockPicking, self).create(vals)
        if vals.get('origin',False):
            order =self.env['sale.order'].search([('name','=',vals.get('origin'))])
            if order and any(e!='cancel' for e in order.customization_ids.mapped('state')):
                res.message_post(
                    body=_('This picking has been created from an order with customized products'))
        return res