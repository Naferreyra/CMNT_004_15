# © 2016 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    is_all_reserved = fields.Boolean(compute='_compute_is_all_reserved',
                                     search='_search_is_all_reserved')
    is_some_reserved = fields.Boolean(compute='_compute_is_some_reserved',
                                      search='_search_is_some_reserved')

    def _action_confirm(self):
        res = super()._action_confirm()
        for sale in self:
            sale.picking_ids.filtered(lambda p: p.state != 'cancel').write({'commercial': sale.user_id.id, 'internal_notes': sale.internal_notes})
            # session = ConnectorSession(self.env.cr, SUPERUSER_ID,
            #                            context=self.env.context)
            # for picking in sale.picking_ids:
            #     if picking.state != 'cancel':
            #         for move in picking.move_lines:
            #             on_record_create.fire(session, 'stock.move',
            #                                   move.id)
            # TODO: Migrar cuando se pueda probar http://odoo-connector.com/guides/migration_guide.html?highlight=fire#triggering-an-event

        return res

    def _search_is_all_reserved(self, operator, operand):
        self.env.cr.execute(
            """
SELECT B.order_id
FROM
(SELECT distinct order_id
 FROM sale_order_line
    INNER JOIN stock_reservation ON stock_reservation.sale_line_id = sale_order_line.id
    INNER JOIN stock_move ON stock_move.id = stock_reservation.move_id
 WHERE stock_move.state != 'assigned') A
RIGHT JOIN
(SELECT distinct order_id
 FROM sale_order_line
    INNER JOIN stock_reservation ON stock_reservation.sale_line_id = sale_order_line.id
    INNER JOIN stock_move ON stock_move.id = stock_reservation.move_id
 WHERE stock_move.state = 'assigned') B
on A.order_id = B.order_id
WHERE A.order_id IS NULL
            """)
        orders = self.env.cr.fetchall()
        order_ids = [x[0] for x in orders]
        if operator == '=' and operand is True:
            return [('id', 'in', order_ids)]
        elif operator == '!=' and operand is True:
            return [('id', 'not in', order_ids)]

    def _compute_is_all_reserved(self):
        for order in self:
            if all([x.state == 'assigned'
                    for x in order.mapped('order_line.reservation_ids')]):
                order.is_all_reserved = True

    def _search_is_some_reserved(self, operator, operand):
        self.env.cr.execute(
            """
SELECT B.order_id
FROM
(SELECT distinct order_id
 FROM sale_order_line
    INNER JOIN stock_reservation ON stock_reservation.sale_line_id = sale_order_line.id
    INNER JOIN stock_move ON stock_move.id = stock_reservation.move_id
 WHERE stock_move.state != 'assigned') A
RIGHT JOIN
(SELECT distinct order_id
 FROM sale_order_line
    INNER JOIN stock_reservation ON stock_reservation.sale_line_id = sale_order_line.id
    INNER JOIN stock_move ON stock_move.id = stock_reservation.move_id
 WHERE stock_move.state = 'assigned') B
on A.order_id = B.order_id
WHERE A.order_id IS NOT NULL
            """)
        orders = self.env.cr.fetchall()
        order_ids = [x[0] for x in orders]
        if operator == '=' and operand is True:
            return [('id', 'in', order_ids)]
        elif operator == '!=' and operand is True:
            return [('id', 'not in', order_ids)]

    def _compute_is_some_reserved(self):
        for order in self:
            order.is_some_reserved = False
            if any([x.state == 'assigned'
                    for x in order.mapped('order_line.reservation_ids')]):
                order.is_some_reserved = True
            if all([x.state == 'assigned'
                    for x in order.mapped('order_line.reservation_ids')]):
                order.is_some_reserved = False

    def action_quotation_send_reserve(self):
        """
            This function opens a window to compose an email,
            with the edi sale template message loaded by default.
        """
        self.ensure_one()
        try:
            template_id = self.env.ref('sale.email_template_edi_sale').id
        except ValueError:
            template_id = False
        try:
            compose_form_id = self.env.ref(
                'sale.email_compose_message_wizard_form').id
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'sale.order',
            'default_res_id': self.id,
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }
