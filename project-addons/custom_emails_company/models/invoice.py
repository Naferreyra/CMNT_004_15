from odoo import models


class AccountInvoice(models.Model):

    _inherit = 'account.invoice'

    def action_invoice_open(self):
        res = super(AccountInvoice, self).action_invoice_open()
        layout = \
            'account.mail_template_data_notification_email_account_invoice'
        for invoice in self:
            if not invoice.not_send_email and invoice.type in ('out_invoice', 'out_refund'):
                try:
                    template = invoice.env.\
                        ref('account.email_template_edi_invoice')
                    report_template ='custom_report_link.action_report_invoice_custom'
                    if invoice.partner_id.send_hs_code_invoice or invoice.partner_id.commercial_partner_id.send_hs_code_invoice:
                        report_template += '_2'
                    template.report_template = invoice.env.ref(report_template)

                except ValueError:
                    template = False

                template.send_mail(invoice.id)
        return res
