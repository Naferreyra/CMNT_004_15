# © 2019 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models
from dateutil.relativedelta import relativedelta


class ResPartnerRappelRel(models.Model):

    _inherit = 'res.partner.rappel.rel'

    def _get_next_period(self):
        self.ensure_one()
        if self.last_settlement_date and \
                self.last_settlement_date > self.date_start:
            date_start = fields.Date.from_string(self.last_settlement_date) + \
                relativedelta(days=1)
        else:
            date_start = fields.Date.from_string(self.date_start)

        date_stop = date_start + relativedelta(
            months=self.PERIODICITIES_MONTHS[self.periodicity], days=-1)
        if self.date_end:
            date_end = fields.Date.from_string(self.date_end)
            if date_end < date_stop:
                date_stop = date_end

        if date_start != date_stop:
            period = [date_start, date_stop]
        else:
            period = False
        return period

    def _get_invoices(self, period, products):
        super()._get_invoices(period, products)
        company_id = self.rappel_id.company_id.id
        invoices = self.env['account.invoice'].search(
            [('type', '=', 'out_invoice'),
             ('date_invoice', '>=', period[0]),
             ('date_invoice', '<=', period[1]),
             ('state', 'in', ['open', 'paid']),
             ('commercial_partner_id', '=', self.partner_id.id),
             ('company_id', '=', company_id)])
        refunds = self.env['account.invoice'].search(
            [('type', '=', 'out_refund'),
             ('date_invoice', '>=', period[0]),
             ('date_invoice', '<=', period[1]),
             ('state', 'in', ['open', 'paid']),
             ('commercial_partner_id', '=', self.partner_id.id),
             ('company_id', '=', company_id)])

        # Si el rappel afecta al catalago entero,
        # no hacer la comprobacion por producto
        if self.rappel_id.global_application:
            refund_lines = self.env['account.invoice.line'].search(
                [('invoice_id', 'in', [x.id for x in refunds]),
                 ('no_rappel', '=', False)])
            invoice_lines = self.env['account.invoice.line'].search(
                [('invoice_id', 'in', [x.id for x in invoices]),
                 ('no_rappel', '=', False)])
        else:
            refund_lines = self.env['account.invoice.line'].search(
                [('invoice_id', 'in', [x.id for x in refunds]),
                 ('product_id', 'in', products),
                 ('no_rappel', '=', False)])
            invoice_lines = self.env['account.invoice.line'].search(
                [('invoice_id', 'in', [x.id for x in invoices]),
                 ('product_id', 'in', products),
                 ('no_rappel', '=', False)])

        return invoice_lines, refund_lines

    def _calculate_pending_to_invoice(self):
        products = self.rappel_id.get_products()
        order_lines = self.env['sale.order.line'].search(
            [('order_id.partner_id', 'child_of', self.partner_id.id),
                ('order_id.state', '=', 'sale'),
                ('product_id', 'in', products),
                ('qty_delivered', '>', 0)])
        order_lines = order_lines.filtered(
            lambda r: r.qty_delivered > r.qty_invoiced)
        return sum(
            [(x.qty_delivered - x.qty_invoiced) *
             (x.price_subtotal / x.product_uom_qty) for x in order_lines])

    @api.model
    def compute(self, period, invoice_lines, refund_lines, tmp_model=False):
        goal_percentage = 0
        rappel_calculated_obj = self.env['rappel.calculated']
        for rappel in self:
            rappel_info = {'rappel_id': rappel.rappel_id.id,
                           'partner_id': rappel.partner_id.id,
                           'date_start': period[0],
                           'amount': 0.0,
                           'amount_est': 0.0,
                           'date_end': period[1]}
            total_rappel = 0.0
            total_rappel_est = 0.0
            if rappel.rappel_id.calc_mode == 'fixed':
                if rappel.rappel_id.calc_amount == 'qty':
                    total_rappel = rappel.rappel_id.fix_qty
                else:
                    total = sum([x.price_subtotal for x in invoice_lines]) - \
                            sum([x.price_subtotal for x in refund_lines])
                    pending_to_invoice = rappel._calculate_pending_to_invoice()
                    total_est = total + pending_to_invoice
                    if total:
                        total_rappel = total * rappel.rappel_id.fix_qty / 100.0
                    if total_est:
                        total_rappel_est = total_est * \
                            rappel.rappel_id.fix_qty / 100.0
                    rappel_info["curr_qty"] = total
                    rappel_info["curr_qty_pickings"] = pending_to_invoice

                rappel_info['amount'] = total_rappel
                rappel_info['amount_est'] = total_rappel_est
            else:
                field = ''
                if rappel.rappel_id.qty_type == 'value':
                    field = 'price_subtotal'
                else:
                    field = 'quantity'
                pending_to_invoice = rappel._calculate_pending_to_invoice()
                total = sum([x[field] for x in invoice_lines]) - \
                    sum([x[field] for x in refund_lines])
                total_est = total + pending_to_invoice
                rappel_info["curr_qty"] = total
                rappel_info["curr_qty_pickings"] = pending_to_invoice

                if self.partner_id.invoice_type_id.name in \
                        ('Mensual', 'Quincenal', 'Semanal') and total_est:
                    rappel_info, goal_percentage, total_rappel = self.compute_total(
                        rappel, total_est, rappel_info, True)
                else:
                    rappel_info['amount_est'] = 0.0

                if total:
                    rappel_info, goal_percentage, total_rappel = self.compute_total(
                        rappel, total, rappel_info, False)
                else:
                    rappel_info['amount'] = 0.0
            total_invoice_ids = [(6,0,(invoice_lines + refund_lines).ids)]
            rappel_info['invoice_line_ids'] = total_invoice_ids

            if period[1] < fields.Date.from_string(fields.Date.today()):
                if total_rappel:
                    rappel_calculated_obj.create({
                        'partner_id': rappel.partner_id.id,
                        'date_start': period[0],
                        'date_end': period[1],
                        'quantity': total_rappel,
                        'rappel_id': rappel.rappel_id.id,
                        'goal_percentage': goal_percentage,
                        'invoice_line_ids': total_invoice_ids
                    })
                    if rappel.rappel_id.discount_voucher and total_rappel > 0:
                        rappel_to_invoice = []
                        rappel_old = rappel_calculated_obj.search_read(
                            [('partner_id', '=', rappel.partner_id.id),
                             ('rappel_id.discount_voucher', '=', True),
                             ('invoice_id', '=', False)], ['id', 'quantity'])
                        amount_total = 0
                        for rp in rappel_old:
                            rappel_to_invoice.append(rp['id'])
                            amount_total += rp['quantity']
                        if amount_total > 0:
                            rappel_calculated_obj.create_rappel_invoice(
                                rappel_to_invoice)
                rappel.last_settlement_date = period[1]
            else:
                if tmp_model and rappel_info:
                    self.env['rappel.current.info'].create(rappel_info)

        return True

    def compute_total(self, rappel, total, rappel_info, estimated):
        total_rappel = 0.0
        section = self.env['rappel.section'].search(
            [('rappel_id', '=', rappel.rappel_id.id),
             ('rappel_from', '<=', total),
             ('rappel_until', '>=', total)])
        if not section:
            section = self.env['rappel.section'].search(
                [('rappel_id', '=', rappel.rappel_id.id),
                 ('rappel_from', '<=', total),
                 ('rappel_until', '=', False)],
                order='rappel_from desc', limit=1)
        if section:
            goal_percentage = 100
        else:
            # Check if goal percentage is more than 80% to get the rappel
            section = self.env['rappel.section'].search(
                [('rappel_id', '=', rappel.rappel_id.id),
                 ('rappel_from', '<=', total / 0.8),
                 ('rappel_from', '>', total)])
            if section.rappel_from:
                goal_percentage = (total / section.rappel_from) * 100
            else:
                goal_percentage = 0

        if not section:
            if estimated:
                rappel_info['amount_est'] = 0.0
            else:
                rappel_info['amount'] = 0.0
        else:
            rappel_info['section_id'] = section.id
            section = section[0]
            if rappel.rappel_id.calc_amount == 'qty':
                total_rappel = section.percent
            else:
                total_rappel = total * section.percent / 100.0
                if estimated:
                    rappel_info['amount_est'] = total_rappel
                else:
                    rappel_info['amount'] = total_rappel
                    rappel_info['amount_est'] = total_rappel

        return rappel_info, goal_percentage, total_rappel
