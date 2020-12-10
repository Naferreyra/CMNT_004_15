# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models, api, registry, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class StockReservation(models.Model):

    _name = 'stock.reservation'
    _inherit = 'stock.reservation'
    _order = "sequence asc"

    def _new_sequence(self):
        query = "SELECT sequence FROM stock_reservation ORDER BY sequence DESC LIMIT 1"
        self.env.cr.execute(query, ())
        regs = self.env.cr.fetchall()
        for reg in regs:
            if not reg[0]:
                seq = 0
            else:
                seq = reg[0]
            sequence = seq + 1
        return sequence

    unique_js_id = fields.Char(size=64)
    sequence = fields.Integer(help='Gives the priority in reservation.',
                              default=_new_sequence, index=True)
    user_id = fields.Many2one('res.users', relation='sale_id.user_id',
                              string='Responsible', readonly=True)
    date_order = fields.Datetime(relation='sale_id.date_order', readonly=True)
    partner_id = fields.Many2one('res.partner', relation='sale_id.partner_id',
                                 readonly=True)

    @api.model
    def create(self, vals):
        context2 = dict(self._context)
        context2.pop('default_state', False)
        res = super(StockReservation, self.with_context(context2)).create(vals)
        res.move_id.user_id = res.user_id
        if vals.get('sequence') and res.move_id:
            res.move_id.sequence = vals['sequence']
        if vals.get('unique_js_id', False) and \
                not vals.get('sale_line_id', False):
            with registry(self.env.cr.dbname).cursor() as new_cr:
                new_env = api.Environment(new_cr, self.env.uid,
                                          self.env.context)

                new_env.cr.execute("select id from sale_order_line where "
                                   "unique_js_id = '%s'" % vals['unique_js_id']
                                   )

                lines = new_env.cr.fetchone()
                if lines:
                    self.with_env(new_env).write({'sale_line_id': lines[0]})
                new_env.cr.commit()
        return res

    def write(self, vals):
        if vals.get('sequence', False):
            old_sequence = self.sequence
            res = super().write(vals)
            self.refresh()
            self.with_context(old_sequence=old_sequence).reassign()
        else:
            res = super().write(vals)
        if vals.get('sequence'):
            for reserve in self:
                reserve.move_id.sequence = vals['sequence']
        elif vals.get('move_id'):
            for reserve in self:
                reserve.move_id.sequence = reserve.sequence
        if vals.get('sale_line_id'):
            for reserve in self:
                reserve.move_id.sale_line_id = vals['sale_line_id']
        return res

    def reassign(self, old_sequence=False):
        self.ensure_one()
        if self.env.context.get('old_sequence'):
            sequence = min(self.env.context['old_sequence'],
                           self.sequence)
        else:
            sequence = self.sequence
        reserv_ids = self.search(
            [('sequence', '>=', sequence),
             ('product_id', '=', self.product_id.id),
             ('state', 'in', ['draft', 'confirmed', 'assigned',
                              'partially_available'])])
        # Undo all reserves in reservations under the first sequence
        reserv_ids.do_complete_release()
        reserv_ids.reserve()
        return True

    def do_complete_release(self):
        for reserve in self:
            if reserve.state in ('done', 'cancel'):
                raise UserError(
                    _('Cannot unreserve a done reserve'))
            reserve.move_id._do_unreserve()
            reserve.write({'state': 'draft'})
            reserve.refresh()

    def reserve(self):
        """ Confirm a reservation
        The reservation is done using the default UOM of the product.
        A date until which the product is reserved can be specified.
        """
        days_release_reserve = self.env['ir.config_parameter'].sudo().get_param('days_to_release_reserve_stock')
        now = datetime.now()
        date_validity = (now + relativedelta(days=int(days_release_reserve))).strftime("%Y-%m-%d")

        moves = self.env['stock.move']
        for reserve in self:
            current_sale_line_id = reserve.sale_line_id.id
            res = super(StockReservation, reserve).reserve()
            reserve.refresh()
            moves |= res
            for move in res:
                reservation = self.env['stock.reservation'].search(
                    [('move_id', '=', move.id)])
                if not reservation:
                    reservation = self.env['stock.reservation'].create(
                        {'move_id': move.id,
                         'sale_line_id': current_sale_line_id,
                         'date_validity': date_validity
                         })
        return moves

    @api.model
    def delete_orphan_reserves(self):
        now = fields.Datetime.now()
        d = datetime.strptime(now, '%Y-%m-%d %H:%M:%S') + \
            timedelta(minutes=-10)
        last_date = datetime.strftime(d, '%Y-%m-%d %H:%M:%S')
        reserves = self.search([('create_date', '<=', last_date),
                                ('sale_line_id', '=', False),
                                ('mrp_id', '=', False),
                                ('claim_id', '=', False),
                                ('move_id.state', 'not in', ['done',
                                                             'cancel'])])

        if reserves:
            reserves.unlink()

        reserves_loc = self.env.ref("stock_reserve.stock_location_reservation")
        moves = self.env["stock.move"].search([('location_dest_id', '=',
                                                reserves_loc.id),
                                               ('state', '!=', "cancel"),
                                               ('reservation_ids', '=',
                                                False)])
        if moves:
            moves._action_cancel()

        reserves = self.search([('create_date', '<=', last_date),
                                ('sale_line_id', '!=', False),
                                ('partner_id', '=', False),
                                ('move_id.state', 'not in', ['done',
                                                             'cancel'])])
        reserves_to_delete = self.env['stock.reservation']
        check_other_reserves = self.\
            search([('sale_line_id', 'in', reserves.mapped('sale_line_id').ids),
                    ('partner_id', '!=', False),
                    ('move_id.state', 'not in', ['done', 'cancel'])])
        if check_other_reserves:
            reserves_to_delete |= reserves.\
                filtered(lambda r: r.sale_line_id.id in check_other_reserves.mapped('sale_line_id').ids)
        if reserves_to_delete:
            reserves_to_delete.unlink()

        return True

    @api.model
    def release_validity_exceeded(self, ids=None):
        domain = [('date_validity', '<', fields.date.today()),
                  ('state', 'in', ('confirmed', 'partially_available', 'assigned'))]
        reservation_to_release = self.search(domain)

        user_ids = reservation_to_release.mapped('move_id.user_id')
        reserve_orders = reservation_to_release.mapped('sale_line_id.order_id')
        # Send email grouping by user
        for user in user_ids:
            orders_user = reserve_orders.filtered(lambda x: x.user_id == user)
            # Prepare email data
            order_data = [order.name + ' (' + order.partner_id.name + ')' for order in orders_user]
            mail_pool = self.env['mail.mail']
            template_obj = self.env.ref('reserve_without_save_sale.mail_template_release_reservations_user')
            ctx = dict(self._context)
            ctx.update({
                'values': order_data
            })
            # Send email
            mail_id = template_obj.with_context(ctx).send_mail(user.id)
            if mail_id:
                mail_id_check = mail_pool.browse(mail_id)
                mail_id_check.send()

        reservation_to_release.release()
        super().release_validity_exceeded(ids)
        return True

    @api.model
    def delete_canceled_reserves(self, interval_dates=[]):
        if not interval_dates:
            now = fields.Datetime.now()
            d1 = datetime.strptime(now, '%Y-%m-%d %H:%M:%S') + \
                 timedelta(days=-7)
            d2 = datetime.strptime(now, '%Y-%m-%d %H:%M:%S') + \
                 timedelta(days=-14)
            start_date = datetime.strftime(d1, '%Y-%m-%d')
            end_date = datetime.strftime(d2, '%Y-%m-%d')
        else:
            start_date = interval_dates[0]
            end_date = interval_dates[1]
        _logger.info("SEARCH CANCELED RESERVATIONS -> STARTING")
        reserves = self.search([('create_date', '>=', start_date),
                                ('create_date', '<', end_date),
                                ('sale_line_id', '=', False),
                                ('mrp_id', '=', False),
                                ('claim_id', '=', False),
                                ('move_id.state', 'in', ['cancel'])])
        _logger.info("SEARCH CANCELED RESERVATIONS -> FINISHED")
        if reserves:
            _logger.info("UNLINK CANCELED RESERVATIONS -> STARTING")
            reserves.unlink()
            _logger.info("UNLINK CANCELED RESERVATIONS -> FINISHED")
