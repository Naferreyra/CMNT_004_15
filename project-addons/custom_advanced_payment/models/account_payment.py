from odoo import models, api


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.multi
    def post(self):
        res = super(AccountPayment, self).post()
        for payment in self:
            if payment.sale_id.invoice_ids:
                debit_receipt_param = self.env['ir.config_parameter'].sudo().get_param('debit.receipt.account.ids')
                account_id = int(debit_receipt_param.split(',')[1])
                move_line = payment.move_line_ids.filtered(lambda m: m.account_id.id == account_id)
                # Paid the invoices with the advanced payment
                for invoice in payment.sale_id.invoice_ids:
                    if invoice.state == 'open' and move_line.amount_residual:
                        invoice.assign_outstanding_credit(move_line.id)
        return res
