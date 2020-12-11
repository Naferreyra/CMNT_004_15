##############################################################################
#
#    Copyright (C) 2015 Comunitea All Rights Reserved
#    $Omar Castiñeira Saavedra <omar@comunitea.com>$
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

from odoo import models, fields, api, _
from odoo.exceptions import Warning


class StockPicking(models.Model):

    _inherit = "stock.picking"

    pending_invoice_move_id = fields.Many2one('account.move',
                                              'Account pending move',
                                              readonly=True,
                                              copy=False)
    pending_stock_reverse_move_id = \
        fields.Many2one('account.move', 'Account pending stock reverse move',
                        readonly=True, copy=False)
    pending_stock_move_id = \
        fields.Many2one('account.move', 'Account pending stock move',
                        readonly=True, copy=False)

    @api.multi
    def account_pending_invoice(self, debit_account, credit_account, date):
        self.ensure_one()
        move_obj = self.env['account.move']
        lines = {}

        origin = self.name
        if self.origin:
            origin += ':' + self.origin

        stock_journal_id = self.company_id.property_pending_stock_journal.id

        move = {
            'ref': origin,
            'journal_id': stock_journal_id,
            'date': date,
        }
        move_id = move_obj.create(move)
        lines_data = []
        obj_precision = self.env['decimal.precision']
        for move_line in self.move_lines:
            name = move_line.name or origin
            amount_line = round(move_line._get_price_unit()*move_line.product_qty, obj_precision.
                                precision_get('Account'))
            vals = {
                'name': name,
                'ref': origin,
                'partner_id': move_line.partner_id.commercial_partner_id.id,
                'product_id': move_line.product_id.id,
                'account_id': debit_account.id,
                'debit': 0,
                'credit': 0,
                'quantity': move_line.product_qty,
                'move_id': move_id.id,
                'journal_id': stock_journal_id,
                'date': date
            }
            if amount_line > 0:
                vals['debit'] = amount_line
            else:
                vals['credit'] = abs(amount_line)
            lines_data.append(vals)
            if move_line.partner_id.commercial_partner_id.id in lines:
                lines[move_line.partner_id.commercial_partner_id.id] += \
                    amount_line
            else:
                lines[move_line.partner_id.commercial_partner_id.id] = \
                    amount_line

        for partner_id in lines:
            vals = {
                'name': name,
                'ref': origin,
                'partner_id': partner_id,
                'account_id': credit_account.id,
                'debit': 0,
                'credit': round(lines[partner_id], obj_precision.
                                precision_get('Account')),
                'move_id': move_id.id,
                'journal_id': stock_journal_id,
                'date': date,
            }
            lines_data.append(vals)
        move_id.line_ids = [(0, 0, x) for x in lines_data]
        move_id.post()

        return move_id

    @api.multi
    def write(self, vals):
        res = super().write(vals)
        if vals.get('date_done'):
            ctx = dict(self._context or {})
            ctx['bypass_risk'] = True
            for pick in self:
                templates = []
                validate = True
                if (pick.picking_type_id.code == "incoming" and pick.move_lines
                        and pick.move_lines[0].purchase_line_id and
                        pick.company_id.required_invoice_pending_move and
                        not pick.pending_stock_reverse_move_id and
                        pick.pending_stock_move_id):
                    pick.refresh()
                    if not pick.company_id.\
                            property_pending_variation_account or not \
                            pick.company_id.property_pending_stock_account:
                        raise Warning(_("You need to configure the accounts "
                                        "in the company for pending invoices"))
                    if not pick.company_id.property_pending_stock_journal:
                        raise Warning(_("You need to configure an account "
                                        "journal in the company for pending "
                                        "invoices"))
                    debit_account = pick.company_id.\
                        property_pending_variation_account
                    credit_account = pick.company_id.\
                        property_pending_stock_account
                    move_id = pick.pending_stock_move_id.\
                        create_reversals(fields.Date.today(),
                                         reconcile=True)
                    pick.pending_stock_reverse_move_id = move_id.id

                if pick.state == 'done' and \
                        pick.picking_type_code == 'outgoing':
                    sale_id = pick.sale_id
                    if (sale_id.invoice_status == 'to invoice'
                        and sale_id.invoice_type_id.name == 'Diaria'
                            and not sale_id.tests):
                        # Create invoice
                        try:
                            id_invoice = sale_id.action_invoice_create()
                            invoice_created = self.env['account.invoice'].\
                                with_context(ctx).browse(id_invoice)
                        except:
                            invoice_created = False
                        if not invoice_created:
                            templates.append(
                                self.env.ref('picking_invoice_pending.alert_picking_autocreate_invoices', False))
                            validate = False
                        elif invoice_created and \
                                not invoice_created.invoice_line_ids:
                            # Invoice created without lines
                            templates.append(
                                self.env.ref('picking_invoice_pending.alert_picking_autocreate_invoices_empty_lines',
                                             False))
                            # Do not validate it because it will generate an error
                            validate = False
                        if validate:
                            try:
                                invoice_created.compute_taxes()
                                invoice_created.action_invoice_open()
                            except:
                                invoice_created.invoice_created_from_picking = True
                                templates.append(
                                    self.env.ref('picking_invoice_pending.alert_picking_autovalidate_invoices', False))

                        for tmpl in templates:
                            ctx.update({
                                'default_model': 'stock.picking',
                                'default_res_id': pick.id,
                                'default_use_template': bool(tmpl.id),
                                'default_template_id': tmpl.id,
                                'default_composition_mode': 'comment',
                                'mark_so_as_sent': True
                            })
                            composer_id = self.env['mail.compose.message'].\
                                with_context(ctx).create({})
                            composer_id.with_context(ctx).send_mail()

        return res

    @api.multi
    def action_confirm(self):
        res = super().action_confirm()
        for pick in self:
            if pick.picking_type_id.code == "incoming" and pick.move_lines \
                    and pick.move_lines[0].purchase_line_id and \
                    pick.company_id.required_invoice_pending_move and \
                    not pick.backorder_id and \
                    not pick.pending_invoice_move_id and \
                    not pick.pending_stock_move_id:
                if not pick.company_id. \
                    property_pending_variation_account or not \
                    pick.company_id.property_pending_stock_account or not \
                    pick.company_id.property_pending_supplier_invoice_account:
                        raise Warning(_("You need to configure the accounts "
                                        "in the company for pending invoices"))
                if not pick.company_id.property_pending_stock_journal:
                    raise Warning(_("You need to configure an account "
                                    "journal in the company for pending "
                                    "invoices"))
                debit_account = pick.company_id.\
                    property_pending_expenses_account
                credit_account = pick.company_id.\
                    property_pending_supplier_invoice_account
                move_id = pick.account_pending_invoice(debit_account,
                                                       credit_account,
                                                       pick.create_date[:10])
                pick.pending_invoice_move_id = move_id.id

                debit_account = pick.company_id.\
                    property_pending_stock_account
                credit_account = pick.company_id.\
                    property_pending_variation_account
                move_id = pick.account_pending_invoice(debit_account,
                                                       credit_account,
                                                       pick.create_date[:10])
                pick.pending_stock_move_id = move_id.id

        return res

    @api.multi
    def action_cancel(self):
        res = super().action_cancel()
        for pick in self:
            if pick.pending_stock_move_id:
                pick.pending_stock_move_id.button_cancel()
                pick.pending_stock_move_id.unlink()
            if pick.pending_invoice_move_id:
                pick.pending_invoice_move_id.button_cancel()
                pick.pending_invoice_move_id.unlink()
            if pick.pending_stock_reverse_move_id:
                pick.pending_stock_reverse_move_id.button_cancel()
                pick.pending_stock_reverse_move_id.unlink()
            if pick.sale_id:
                picking_states = self.env['stock.picking'].search_read([('sale_id', '=', pick.sale_id.id)],
                                                                       ['state'])

                if all(picking['state'] in ('done', 'cancel') for picking in picking_states):
                    if all(picking['state'] == 'cancel' for picking in picking_states):
                        pick.sale_id.state = 'cancel'
                    else:
                        pick.sale_id.action_done()
        return res

    @api.multi
    def unlink(self):
        for pick in self:
            if pick.pending_stock_move_id:
                pick.pending_stock_move_id.button_cancel()
                pick.pending_stock_move_id.unlink()
            if pick.pending_invoice_move_id:
                pick.pending_invoice_move_id.button_cancel()
                pick.pending_invoice_move_id.unlink()
            if pick.pending_stock_reverse_move_id:
                pick.pending_stock_reverse_move_id.button_cancel()
                pick.pending_stock_reverse_move_id.unlink()
        return super().unlink()


class StockMove(models.Model):

    _inherit = 'stock.move'

    @api.multi
    def _get_price_unit(self):
        """ Returns the unit price for the move"""
        self.ensure_one()
        if self.purchase_line_id and self.product_id.id == self.purchase_line_id.product_id.id:
            line = self.purchase_line_id
            order = line.order_id
            price_unit = line.price_unit
            if line.taxes_id:
                price_unit = line.taxes_id.\
                    with_context(round=False).\
                    compute_all(price_unit, currency=line.order_id.currency_id, quantity=1.0)['total_excluded']
            if line.product_uom.id != line.product_id.uom_id.id:
                price_unit *= line.product_uom.factor / line.product_id.uom_id.factor
            if order.currency_id != order.company_id.currency_id:
                # Set date as picking creation date
                if self.picking_id and self.picking_id.picking_type_id.code == "incoming":
                    picking = self.picking_id
                    if picking.backorder_id:
                        date = picking.backorder_id.date
                    else:
                        date = picking.date
                else:
                    date = fields.Date.context_today(self)
                price_unit = order.currency_id.with_context(date=date).\
                    compute(price_unit, order.company_id.currency_id, round=False)
            return price_unit
        return super(StockMove, self)._get_price_unit()

