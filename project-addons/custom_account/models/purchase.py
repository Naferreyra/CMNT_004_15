# Copyright 2019 Omar Castiñeira, Comunitea Servicios Tecnológicos S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields,api, models, _, exceptions


class PurchaseOrder(models.Model):

    _inherit = "purchase.order"

    def button_cancel(self):
        for purchase in self:
            done_moves = purchase.order_line.mapped('move_ids').\
                filtered(lambda x: x.state == 'done')
            if done_moves:
                raise exceptions.\
                    UserError(_('Unable to cancel purchase order %s as '
                                'some receptions have already been done.') %
                              (purchase.name))
            else:
                purchase.picking_ids.action_cancel()
                purchase.order_line.mapped('move_ids').\
                    write({'state': 'cancel'})
        super().button_cancel()

    manufacture_date = fields.Date("Manufacture Date",
                                   help="Date when it was manufactured")
    prepared_merchandise_date = \
        fields.Date("Prepared Merchandise Date",
                    help="Date when the merchandise was prepared")
    estimated_arrival_date = fields.\
        Date("Estimated Arrival Date",
             help="Date when the merchandise will arrive approximately")
    telex_release = fields.\
        Boolean("Telex Release",
                help="It indicates that Telex release is necessary")
    end_manufacture = fields.Date("Ending Date Of Manufacture")
    sale_notes = fields.Text("Purchase Sale Notes")
    remark = fields.Char("Remark")
    send_date_planned_to_lines = fields.Boolean("Set date to all order lines",default=True)

    @api.multi
    def button_confirm(self):
        for order in self:
            if order.send_date_planned_to_lines:
                order.action_set_date_planned()
        return super().button_confirm()
