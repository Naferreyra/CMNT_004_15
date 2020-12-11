# © 2019 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class RappelCurrentInfo(models.Model):

    _inherit = 'rappel.current.info'

    curr_qty_pickings = fields.Float("Qty pending invoice", readonly=True,
                                     help="Qty estimation in pickings pending to be invoiced (shipping cost and"
                                          "product with no-rappel in the order are not verified)")
    amount_est = fields.Float("Estimated amount", readonly=True, default=0.0)

    invoice_line_ids = fields.Many2many('account.invoice.line',readonly=True)

    @api.model
    def send_rappel_info_mail(self):
        mail_pool = self.env['mail.mail']
        mail_ids = self.env['mail.mail']
        partners_with_rappels = self.env['res.partner'].search(
            [('rappel_ids', '!=', '')])
        for partner in partners_with_rappels:
            rappel_infos = self.search([('partner_id', '=', partner.id)])
            send = False
            if rappel_infos:

                values = {}
                for rappel in rappel_infos:
                    date_end = fields.Date.from_string(rappel.date_end)
                    date_start = fields.Date.from_string(rappel.date_start)
                    today = fields.Date.from_string(fields.Date.today())

                    for rappel_timing in rappel.rappel_id.advice_timing_ids:

                        if rappel_timing.advice_timing == 'fixed':
                            timing = (date_end - today).days
                            if timing == rappel_timing.timing:
                                send = True

                        if rappel_timing.advice_timing == 'variable':

                            timing = round((date_end - date_start).days * \
                                rappel_timing.timing / 100)
                            timing2 = (today - date_start).days

                            if timing == timing2:
                                send = True

                        if send and rappel.curr_qty:
                            values.setdefault(partner.id, []).append({
                                'concepto': rappel.rappel_id.name,
                                'date_start': date_start.strftime('%d/%m/%Y'),
                                'date_end': date_end.strftime('%d/%m/%Y'),
                                'advice_timing': rappel_timing.advice_timing,
                                'timing': rappel_timing.timing,
                                'curr_qty': rappel.curr_qty,
                                'section_goal': rappel.section_goal,
                                'section_id': rappel.section_id,
                                'amount': rappel.amount
                            })
                        send = False

                if values.get(partner.id):
                    template = self.env.ref('rappel_custom.rappel_mail_advice')
                    ctx = dict(self._context)
                    ctx.update({
                        'partner_email': partner.email,
                        'partner_id': partner.id,
                        'partner_lang': partner.lang,
                        'partner_name': partner.name,
                        'mail_from': self.env.user.company_id.email,
                        'values': values[partner.id]
                    })

                    mail_id = template.with_context(ctx).send_mail(
                        rappel.partner_id.id)
                    mail_ids += mail_pool.browse(mail_id)
        if mail_ids:
            mail_ids.send()
