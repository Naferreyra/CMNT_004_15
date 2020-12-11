from odoo import models, fields, api, _
import ftplib
import io
import base64


class AccountInvoice(models.Model):

    _inherit = 'account.invoice'

    @api.multi
    def send_via_edi(self):
        for invoice in self:
            edi_msg = self.env['edif.message'].generate_invoice(invoice)
            filename = 'VT-{}.EDI'.format(invoice.number.replace("/", "-"))

            fileb = io.BytesIO()
            fileb.write(edi_msg.encode('latin-1'))
            fileb.seek(0)  # This allows to reads from the start of the stream

            ftp_dir = self.env['ir.config_parameter'].sudo().get_param('ftp_edi_dir')
            ftp_user = self.env['ir.config_parameter'].sudo().get_param('ftp_edi_user')
            ftp_pass = self.env['ir.config_parameter'].sudo().get_param('ftp_edi_pass')
            ftp_folder_out = self.env['ir.config_parameter'].sudo().get_param('ftp_edi_folder_out')

            ftp = ftplib.FTP(ftp_dir)
            ftp.login(user=ftp_user, passwd=ftp_pass)
            ftp.cwd(ftp_folder_out)
            try:
                ftp.storbinary("STOR %s" % filename, fileb)
            except ftplib.error_perm:
                self.send_edi_error_mail()

            ftp.quit()

            ctx = {}
            self.env['ir.attachment'].with_context(ctx).create({
                'name': filename,
                'res_id': invoice.id,
                'res_model': str(invoice._name),
                'datas': base64.b64encode(fileb.getvalue()),
                'datas_fname': filename,
                'type': 'binary',
            })

    @api.multi
    def invoice_validate(self):
        res = super(AccountInvoice, self).invoice_validate()
        for invoice in self.filtered(lambda i: i.partner_id.commercial_partner_id.edi_enabled):
            invoice.send_via_edi()

        return res

    @api.multi
    def send_edi_error_mail(self):
        mail_pool = self.env['mail.mail']
        context = self._context.copy()
        context.pop('default_state', False)

        template_id = self.env.ref('edi_edifact.email_template_edi_send_error')

        if template_id:
            mail_id = template_id.with_context(context).send_mail(self.id)
            if mail_id:
                mail_id_check = mail_pool.browse(mail_id)
                mail_id_check.with_context(context).send()

        return True
