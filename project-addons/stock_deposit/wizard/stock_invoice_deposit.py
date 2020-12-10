##############################################################################
#
#    Copyright (C) 2015 Pexego All Rights Reserved
#    $Jesús Ventosinos Mayor <jesus@pexego.es>$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import models, fields, api, exceptions, _


class StockInvoiceDeposit(models.TransientModel):
    _name = 'stock.invoice.deposit'

    def _get_journal(self):
        journal_obj = self.env['account.journal']
        deposit_obj = self.env['stock.deposit']
        deposits = deposit_obj.browse(self._context['active_ids'])
        sale_invoice_types = deposits.mapped('sale_id.invoice_type_id')
        if len(sale_invoice_types.mapped('journal_id')) > 1 \
                or (sale_invoice_types.mapped('journal_id')
                    and sale_invoice_types.filtered(lambda d: not d.journal_id)):
            raise exceptions.Warning(_('There are two or more different account journals. '
                                       'Please, make sure to select sale orders with the same journal.'))
        elif deposits.mapped('sale_id.invoice_type_id.journal_id'):
            journals = deposits.mapped('sale_id.invoice_type_id.journal_id')
        else:
            journals = journal_obj.search([('type', '=', 'sale')])
        return journals and journals[0] or False

    journal_id = fields.Many2one('account.journal', 'Destination Journal',
                                 required=True, default=_get_journal)

    @api.multi
    def create_invoice(self):
        deposit_obj = self.env['stock.deposit']
        deposit_ids = self.env.context['active_ids']
        deposits = deposit_obj.search([('id', 'in', deposit_ids),
                                       ('state', '=', 'sale')])
        invoice_ids = []
        if not deposits:
            raise exceptions.Warning(_('No deposit selected'))
        sales = list(set([x.sale_id for x in deposits]))
        for sale in sales:
            sale_deposit = deposit_obj.search(
                [('id', 'in', deposit_ids), ('sale_id', '=', sale.id)])

            sale_lines = self.env['sale.order.line']
            for deposit in sale_deposit:
                sale_lines += deposit.move_id.sale_line_id
            my_context = dict(self.env.context)
            my_context['invoice_deposit'] = True
            inv_vals = sale._prepare_invoice()
            inv_vals['journal_id'] = self.journal_id.id
            if not inv_vals.get("payment_term_id", False):
                inv_vals['payment_term_id'] = \
                    sale.partner_id.property_payment_term_id.id
            if not inv_vals.get("payment_mode_id", False):
                inv_vals['payment_mode_id'] = \
                    sale.partner_id.customer_payment_mode_id.id
            if not inv_vals.get("partner_bank_id", False):
                inv_vals['partner_bank_id'] = sale.partner_id.bank_ids \
                    and sale.partner_id.bank_ids[0].id or False
            invoice = self.env['account.invoice'].create(inv_vals)
            for line in sale_lines:
                line.with_context(my_context).invoice_line_create(invoice.id, line.qty_to_invoice)
            invoice_ids.append(invoice.id)
            sale_deposit.write({'invoice_id': invoice.id})
        deposits.write({'state': 'invoiced'})
        action = self.env.ref('account.action_invoice_tree1').read()[0]
        action['domain'] = \
            "[('id','in', [" + ','.join(map(str, invoice_ids)) + "])]"
        return action
