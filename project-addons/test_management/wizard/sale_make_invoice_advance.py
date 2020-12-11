# © 2019 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields, _, exceptions, api


class SaleAdvancePaymentInv(models.TransientModel):

    _inherit = 'sale.advance.payment.inv'

    @api.model
    def _get_default_invoice_on_test(self):
        sale_obj = self.env['sale.order']
        orders = sale_obj.browse(self._context.get('active_ids'))
        if all(x.tests for x in orders):
            return True
        elif all(not x.tests for x in orders):
            return False
        else:
            raise exceptions.Warning(
                _('You are trying to invoice normal and test invoice together')
            )

    invoice_on_test = fields.Boolean(default=_get_default_invoice_on_test)

    @api.multi
    def create_invoices(self):
        sale_orders = self.env['sale.order'].browse(
            self._context.get('active_ids', []))
        res = super().create_invoices()
        if self.invoice_on_test:
            orders = self.env['sale.order']
            for invoice_id in sale_orders.mapped('invoice_ids')._ids:
                invoice = self.env['account.invoice'].sudo().browse(invoice_id)
                if invoice.state == 'draft':
                    test_company_id = self.env.user.company_id.test_company_id.id
                    test_account = self.env["account.account"].sudo().search(
                        [('code', 'like', invoice.account_id.code),
                         ('company_id', '=', test_company_id)], limit=1)
                    test_journal = self.env['account.journal'].sudo().\
                        search([('type', '=', 'sale'),
                                ('company_id', '=', test_company_id)], limit=1)
                    invoice.write({
                        'company_id': test_company_id,
                        'fiscal_position_id': False,
                        'payment_term_id': False,
                        'payment_mode_id': False,
                        'partner_bank_id': False,
                        'mandate_id': False,
                        'journal_id': test_journal.id,
                        'tax_line_ids': [(6, 0, [])],
                        'account_id': test_account.id,
                        'not_send_email': True,
                        'allow_confirm_blocked': True
                    })

                    invoice.partner_id.company_id = False
                    invoice.commercial_partner_id.company_id = False
                    for line in invoice.invoice_line_ids:
                        accounts = self.env["account.account"].sudo().search(
                            [('code', 'like', line.account_id.code),
                             ('company_id', '=', test_company_id)], limit=1)
                        orders |= line.sale_line_ids.mapped('order_id')
                        line.write({'sale_line_ids': [(6, 0, [])],
                                    'invoice_line_tax_ids': [(6, 0, [])],
                                    'company_id': test_company_id,
                                    'account_id': accounts.id,
                                    'account_analytic_id': False})
                        if line.product_id:
                            line.product_id.company_id = False

                    invoice._onchange_invoice_line_ids()
            orders.write({'force_invoiced':  True})
            orders.mapped('order_line').filtered(lambda l:l.invoice_status=='to invoice').write({'invoice_status': 'no'})
        orders_to_done = self.env['sale.order']
        for order in sale_orders:
            if not order.order_line.mapped('product_id').filtered(lambda x: x.type != 'service'):
                orders_to_done += order
        orders_to_done.write({'state': 'done'})
        return res
