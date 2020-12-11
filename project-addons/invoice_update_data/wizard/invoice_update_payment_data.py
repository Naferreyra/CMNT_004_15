# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields, api, _
from odoo.exceptions import Warning


class OrderCheckPricesWizardBrands(models.TransientModel):

    _name = 'invoice.update.payment.data.invoices'

    wizard_id = fields.Many2one('invoice.update.payment.data')
    invoice_id = fields.Many2one('account.invoice', "Invoice")


class InvoiceUpdatePaymentData(models.TransientModel):

    _name = 'invoice.update.payment.data'

    action = fields.Selection([('debit_receipt', 'Update to debit receipt'),
                               ('mandate', 'Update valid mandate')], "Action",
                              required=True, default='debit_receipt')
    partner_id = fields.Many2one('res.partner', "Partner", required=True)
    option = fields.Selection([('open_invoices', 'All open invoices'),
                               ('select_invoices', 'Select invoices')], "Option",
                              required=True, default='open_invoices')
    partner_invoices_filtered = fields.One2many('invoice.update.payment.data.invoices', 'wizard_id', "Invoices")
    info = fields.Text("Information", readonly=True)

    @api.multi
    def update_invoice_data(self):
        view = self.env.ref('invoice_update_data.update_invoice_payment_data_wizard_info').id
        debit_receipt_param = self.env['ir.config_parameter'].sudo().get_param('debit.receipt.account.ids')
        debit_receipt = int(debit_receipt_param.split(',')[0])
        account_id = int(debit_receipt_param.split(',')[1])
        debit_receipt_mode_id = self.env['account.payment.mode'].browse([debit_receipt]).id

        if self.option == 'select_invoices':
            invoice_filter = self.partner_invoices_filtered.mapped('invoice_id')
        else:
            invoice_filter = self.env['account.invoice'].search([('partner_id', 'child_of', [self.partner_id.id]),
                                                                 ('state', '=', 'open')])
        account_move_lines = self.env['account.move.line'].search([('full_reconcile_id', '=', False),
                                                                   ('account_id', '=', account_id),
                                                                   ('invoice_id', 'in', invoice_filter.ids)])
        valid_mandate = self.partner_id.valid_mandate_id.id
        if not valid_mandate:
            raise Warning(_("There is not a valid mandate for this partner"))
        else:
            if self.action == 'debit_receipt':
                invoice_filter.write({'payment_mode_id': debit_receipt_mode_id,
                                      'mandate_id': valid_mandate})
                account_move_lines.write({'payment_mode_id': debit_receipt_mode_id,
                                          'mandate_id': valid_mandate})
            elif self.action == 'mandate':
                invoice_filter.write({'mandate_id': valid_mandate})
                account_move_lines.write({'mandate_id': valid_mandate})

        self.info = (_("Updated invoices: %s") % (invoice_filter.mapped('number')))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Info changes'),
            'res_model': 'invoice.update.payment.data',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view,
            'res_id': self.id
        }

