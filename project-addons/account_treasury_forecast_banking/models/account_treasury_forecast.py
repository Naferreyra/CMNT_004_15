##############################################################################
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################

from odoo import models, fields, api


class AccountTreasuryForecastInvoice(models.Model):
    _inherit = 'account.treasury.forecast.invoice'

    payment_mode_id = fields.Many2one('account.payment.mode', string="Payment Mode",
                                      store=True,
                                      related="invoice_id.payment_mode_id")
    invoice_type = fields.Selection([('out_invoice', 'Customer Invoice'),
                                     ('in_invoice', 'Supplier Invoice'),
                                     ('out_refund', 'Customer Refund'),
                                     ('in_refund', 'Supplier Refund')],
                                    string="Type", related='invoice_id.type')
    payment_term_id = fields.Many2one('account.payment.term',
                                      string="Payment Term",
                                      related='invoice_id.payment_term_id')


class AccountTreasuryForecastLine(models.Model):
    _inherit = 'account.treasury.forecast.line'

    payment_mode_id = fields.Many2one('account.payment.mode', string="Payment Mode")


class AccountTreasuryForecast(models.Model):
    _inherit = 'account.treasury.forecast'

    @api.multi
    def calculate_line(self):
        treasury_line_obj = self.env['account.treasury.forecast.line']
        for record in self:
            result = super(AccountTreasuryForecast, record).calculate_line()
            line_lst = treasury_line_obj.search([('treasury_id', '=', record.id)])
            for line_o in line_lst:
                payment_mode_id = line_o.template_line_id.payment_mode_id.id
                line_o.payment_mode_id = payment_mode_id
        return result
