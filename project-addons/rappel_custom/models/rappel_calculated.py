# © 2019 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models
from datetime import datetime,timedelta


class RappelCalculated(models.Model):

    _inherit = 'rappel.calculated'

    _order = 'date_end desc'

    goal_percentage = fields.Float()

    invoice_line_ids = fields.Many2many('account.invoice.line',readonly=True)

    @api.model
    def create_rappel_invoice(self, rappels_to_invoice):
        # Journal = Sales refund (SCNJ)
        journal_id = self.env['account.journal'].search(
            [('type', '=', 'sale')], order='id')[0].id

        # Prepare context to call action_invoice method
        ctx = dict(self._context or {})
        ctx['active_ids'] = rappels_to_invoice
        ctx['active_id'] = rappels_to_invoice[0]

        rappel_invoice_wzd = self.env['rappel.invoice.wzd']
        invoice_data = {'journal_id': journal_id,
             'group_by_partner': True,
             'invoice_date': False}
        today = datetime.today()
        if today.day==1:
            yesterday = today - timedelta(days=1)
            invoice_data['invoice_date'] = yesterday
        new_data_invoice = rappel_invoice_wzd.with_context(ctx).create(invoice_data)

        # Create invoice
        new_data_invoice.action_invoice()

        invoice = self.browse(rappels_to_invoice).mapped('invoice_id')

        # Insert negative lines in the created invoice
        if len(rappels_to_invoice) > 1:
            invoice_line_obj = self.env["account.invoice.line"]
            for rp in self.browse(rappels_to_invoice):
                if not rp.invoice_id:
                    rappel_product = rp.rappel_id.type_id.product_id
                    account_id = rappel_product.property_account_income_id
                    if not account_id:
                        account_id = rappel_product.categ_id. \
                            property_account_income_categ_id
                    taxes_ids = rappel_product.taxes_id
                    fpos = rp.partner_id.property_account_position_id or False
                    if fpos:
                        account_id = fpos.map_account(account_id)
                        taxes_ids = fpos.map_tax(taxes_ids)
                    tax_ids = [(6, 0, [x.id for x in taxes_ids])]
                    ctx = dict(rp.rappel_id._context or {})
                    ctx['lang'] = rp.partner_id.lang
                    invoice_line_obj.create({'product_id': rappel_product.id,
                                             'name': '{} ({} - {})'.format(
                                                            rp.rappel_id.with_context(ctx).description,
                                                            datetime.strptime(rp.date_start, "%Y-%m-%d").strftime('%d/%m/%Y'),
                                                            datetime.strptime(rp.date_end, "%Y-%m-%d").strftime('%d/%m/%Y')),
                                             'invoice_id': invoice.id,
                                             'account_id': account_id.id,
                                             'invoice_line_tax_ids': tax_ids,
                                             'price_unit': rp.quantity,
                                             'quantity': 1})
                    rp.invoice_id = invoice.id

        invoice.compute_taxes()
        invoice.action_invoice_open()
        return True
