from odoo import models, api
from statistics import mean

class StockPicking(models.Model):

    _inherit = 'stock.picking'

    @api.multi
    def action_done(self):
        res = super().action_done()
        for picking in self:
            if picking.picking_type_id.code == "outgoing":
                for move in picking.move_lines:
                    if move.move_orig_ids:
                        cost = mean(move.move_orig_ids.mapped('price_unit'))
                        move.price_unit =  cost * -1
                        move.invoice_line_ids.write({'cost_unit':cost})
        return res

