##############################################################################
#
#    Copyright (C) 2016 Comunitea All Rights Reserved
#    $Jesús Ventosinos Mayor <jesus@comunitea.com>$
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
from odoo import models, fields, api


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    invoice_type_id = fields.Many2one('res.partner.invoice.type', "Invoice type")

    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        super().onchange_partner_id()
        if self.partner_id:
            part = self.partner_id
            self.invoice_type_id = part.invoice_type_id and part.invoice_type_id.id \
                or part.commercial_partner_id.invoice_type_id and part.commercial_partner_id.invoice_type_id.id \
                or False

    @api.model
    def cron_create_invoices(self):
        sale_obj = self.env['sale.order']
        ctx = dict(self._context or {})
        ctx['bypass_risk'] = True
        templates = []
        validate = True

        # Sales to Invoice
        sales = sale_obj.\
            search([('invoice_status_2', '=', 'to_invoice'),
                    ('invoice_type_id.name', '=', 'Diaria'),
                    ('tests', '=', False)],
                   order='confirmation_date')

        # Create invoice
        res = []
        for sale in sales:
            try:
                invoices = sale.action_invoice_create()
                res.extend(invoices)
            except:
                print("No invoiceable lines on sale {}".format(sale.name))
                invoices = self.env['account.invoice'].\
                    search([('state', '=', 'draft'),
                            ('origin', '=', sale.name)])
                if invoices:
                    invoices.unlink()
                pass

        if len(sales) != len(res):
            templates.append(self.env.ref('picking_invoice_pending.alert_cron_create_invoices', False))
        invoices_created = self.env['account.invoice'].with_context(ctx).\
            browse(res)
        if len(res) != len(invoices_created.mapped('invoice_line_ids.invoice_id.id')):
            # There are invoices created without lines
            templates.append(self.env.ref('picking_invoice_pending.alert_cron_create_invoices_empty_lines', False))
            # Do not validate them because it will generate an error
            validate = False
        if validate:
            # Validate invoice
            invoices_created.action_invoice_open()
            invoice_states = invoices_created.mapped('state')
            if 'draft' in invoice_states or 'cancel' in invoice_states or \
                    'proforma' in invoice_states or \
                    'proforma2' in invoice_states:
                templates.append(self.env.ref('picking_invoice_pending.alert_cron_validate_invoices', False))
        if invoices_created:
            for tmpl in templates:
                ctx.update({
                    'default_model': 'account.invoice',
                    'default_res_id': invoices_created[0].id,
                    'default_use_template': bool(tmpl.id),
                    'default_template_id': tmpl.id,
                    'default_composition_mode': 'comment',
                    'mark_so_as_sent': True
                })
                composer_id = self.env['mail.compose.message'].\
                    with_context(ctx).create({})
                composer_id.with_context(ctx).send_mail()

        return True

    @api.multi
    def action_invoice_create(self, grouped=False, final=False):
        res = super(SaleOrder, self).action_invoice_create(grouped=grouped, final=final)
        orders_to_done = self.env['sale.order']
        for order in self:
            if not order.order_line.mapped('product_id').filtered(lambda x: x.type != 'service'):
                orders_to_done += order
        orders_to_done.write({'state': 'done'})
        return res

    @api.multi
    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        invoice_type = (self.invoice_type_id
                        or self.partner_id.commercial_partner_id.invoice_type_id)
        if invoice_type and invoice_type.journal_id:
            res['journal_id'] = invoice_type.journal_id.id
        return res

