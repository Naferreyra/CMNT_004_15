# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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
from openerp import models, fields, tools, api, exceptions, _
import openerp.addons.decimal_precision as dp

PAYMENT_MODE = [('debit_receipt', 'Debit receipt'),
                ('transfer', 'Transfer'),
                ('both', 'Both')]


class AccountTreasuryForecast(models.Model):
    _inherit = "account.treasury.forecast"

    payment_mode_customer = fields.Selection(PAYMENT_MODE, 'Payment mode', default='both')
    account_bank = fields.Many2one('res.partner.bank', 'Account bank',
                                   domain=lambda self: [('partner_id', '=', self.env.user.company_id.partner_id.id)])
    check_old_open_customer = fields.Boolean(string="Old (opened)")
    opened_start_date_customer = fields.Date(string="Start Date")
    payment_mode_supplier = fields.Selection(PAYMENT_MODE, 'Payment mode', default='both')
    check_old_open_supplier = fields.Boolean(string="Old (opened)")
    opened_start_date_supplier = fields.Date(string="Start Date")
    not_bankable_supplier = fields.Boolean(string="Without Bankable Suppliers")

    @api.one
    @api.constrains('payment_mode_customer', 'check_old_open_customer',
                    'payment_mode_supplier', 'check_old_open_supplier',
                    'opened_start_date_customer', 'opened_start_date_supplier', 'start_date')
    def check_filter(self):
        if not self.payment_mode_customer or not self.payment_mode_supplier:
            raise exceptions.Warning(
                _('Error!:: You must select one option for payment mode fields.'))
        elif self.payment_mode_customer != 'debit_receipt':
            if self.check_old_open_customer:
                if self.opened_start_date_customer >= self.start_date:
                    raise exceptions.Warning(
                        _('Error!:: Start date of old opened invoices in customers must be lower '
                          'than the start date specified before.'))
        elif self.payment_mode_supplier != 'debit_receipt':
            if self.check_old_open_supplier:
                if self.opened_start_date_supplier >= self.start_date:
                    raise exceptions.Warning(
                        _('Error!:: Start date of old opened invoices in suppliers must be lower '
                          'than the start date specified before.'))

    @api.one
    def calculate_invoices(self):
        invoice_obj = self.env['account.invoice']
        treasury_invoice_obj = self.env['account.treasury.forecast.invoice']
        new_invoice_ids = []
        in_invoice_lst = []
        out_invoice_lst = []

        # CUSTOMER
        search_filter_customer = ['&', ('type', 'in', ['out_invoice', 'out_refund'])]
        if self.payment_mode_customer == 'debit_receipt':
            search_filter_customer.extend([('payment_mode_id.treasury_forecast_type', '=', 'debit_receipt'),
                                           ('state', 'in', ['open', 'paid']),
                                           ('date_due', '>=', self.start_date), ('date_due', '<=', self.end_date)])
        else:
            if self.payment_mode_customer == 'both':
                search_filter_customer.extend(['|',
                                               '&', ('payment_mode_id.treasury_forecast_type', '=', 'debit_receipt'),
                                               '&', ('state', 'in', ['open', 'paid']),
                                               '&', ('date_due', '>=', self.start_date),
                                               ('date_due', '<=', self.end_date)])

            if self.account_bank:
                search_filter_customer.extend(['&', ('payment_mode_id.bank_id', '=', self.account_bank.id)])

            if self.check_old_open_customer:
                start_date = self.opened_start_date_customer
            else:
                start_date = self.start_date

            search_filter_customer.extend(['&', ('payment_mode_id.treasury_forecast_type', '=', 'transfer'),
                                           '&', ('state', '=', 'open'),
                                           '&', ('date_due', '>=', start_date), ('date_due', '<=', self.end_date)])
        invoice_ids = invoice_obj.search(search_filter_customer, order='date_due asc, id asc')
        for invoice_o in invoice_ids:
            values = {
                'invoice_id': invoice_o.id,
                'date_due': invoice_o.date_due,
                'partner_id': invoice_o.partner_id.id,
                'journal_id': invoice_o.journal_id.id,
                'state': invoice_o.state,
                'base_amount': invoice_o.amount_untaxed,
                'tax_amount': invoice_o.amount_tax,
                'total_amount': invoice_o.amount_total,
                'residual_amount': invoice_o.residual,
            }
            new_id = treasury_invoice_obj.create(values)
            new_invoice_ids.append(new_id)
            out_invoice_lst.append(new_id.id)

        # SUPPLIER
        search_filter_supplier = ['&', '&', ('type', 'in', ['in_invoice', 'in_refund']),
                                  ('partner_id.commercial_partner_id', '!=', 148435)]  # Omit AEAT invoices

        if self.payment_mode_supplier == 'debit_receipt':
            search_filter_supplier.extend([('payment_mode_id.treasury_forecast_type', '=', 'debit_receipt'),
                                           ('state', 'in', ['open', 'paid']),
                                           ('date_due', '>=', self.start_date), ('date_due', '<=', self.end_date)])
        else:
            if self.payment_mode_supplier == 'both':
                search_filter_supplier.extend(['|',
                                               '&',
                                               ('payment_mode_id.treasury_forecast_type', '=', 'debit_receipt'),
                                               '&', ('state', 'in', ['open', 'paid']),
                                               '&', ('date_due', '>=', self.start_date),
                                               ('date_due', '<=', self.end_date)])

            if self.check_old_open_supplier:
                start_date = self.opened_start_date_supplier
            else:
                start_date = self.start_date

            if self.not_bankable_supplier:
                id_currency_usd = self.env.ref("base.USD").id
                search_filter_supplier.extend(['&', '|', ('partner_id.property_product_pricelist_purchase.currency_id',
                                                          '!=', id_currency_usd),
                                               ('partner_id.property_account_payable.code', '!=', '40000000')])

            search_filter_supplier.extend(['&', ('payment_mode_id.treasury_forecast_type', '=', 'transfer'),
                                           '&', ('state', '=', 'open'),
                                           '&', ('date_due', '>=', start_date), ('date_due', '<=', self.end_date)])

        invoice_ids = invoice_obj.search(search_filter_supplier, order='date_due asc, id asc')
        for invoice_o in invoice_ids:
            values = {
                'invoice_id': invoice_o.id,
                'date_due': invoice_o.date_due,
                'partner_id': invoice_o.partner_id.id,
                'journal_id': invoice_o.journal_id.id,
                'state': invoice_o.state,
                'base_amount': invoice_o.amount_untaxed,
                'tax_amount': invoice_o.amount_tax,
                'total_amount': invoice_o.amount_total,
                'residual_amount': invoice_o.residual,
            }
            new_id = treasury_invoice_obj.create(values)
            new_invoice_ids.append(new_id)
            in_invoice_lst.append(new_id.id)

        self.write({'out_invoice_ids': [(6, 0, out_invoice_lst)],
                    'in_invoice_ids': [(6, 0, in_invoice_lst)]})

        return new_invoice_ids


class ReportAccountTreasuryForecastAnalysis(models.Model):
    _inherit = 'report.account.treasury.forecast.analysis'
    _order = 'treasury_id asc, date asc, id_ref asc'

    id_ref = fields.Char(string="Id Reference")
    concept = fields.Char(string="Concept")
    partner_id = fields.Many2one('res.partner', string='Partner/Supplier')
    bank_id = fields.Many2one('res.partner.bank', string='Bank Account')
    accumulative_balance = fields.Float(string="Accumulated", digits_compute=dp.get_precision('Account'))

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_account_treasury_forecast_analysis')
        cr.execute("""
            create or replace view report_account_treasury_forecast_analysis
                as (
                    SELECT	    analysis.id, 
                                analysis.treasury_id, 
                                analysis.id_ref, 
                                analysis.date, 
                                analysis.concept, 
                                rp.id as partner_id, 
                                analysis.payment_mode_id,
                                pm.bank_id,
                                analysis.credit, 
                                analysis.debit, 
                                analysis.balance, 
                                analysis.type,
                                sum(balance) OVER (PARTITION BY analysis.treasury_id
                                            ORDER BY analysis.treasury_id desc, analysis.date, analysis.id_ref) AS accumulative_balance
                            FROM (
                                select  '0' as id,
                                    0 as id_ref,
                                    'Importe inicial' as concept,
                                    tf.id as treasury_id,
                                    tf.start_date as date,
                                    null as credit,
                                    null as debit,
                                    start_amount as balance,
                                    null as payment_mode_id,
                                    null as type,
                                    null partner_id
                                from    account_treasury_forecast tf 
                                where   tf.start_amount > 0 -- Incluir linea de importe inicial
                                union
                                select
                                    tfl.id || 'l' AS id,
                                    tfl.id as id_ref,
                                    tfl.name as concept,
                                    treasury_id,
                                    tfl.date as date,
                                    CASE WHEN tfl.line_type='receivable' THEN 0.0
                                    ELSE amount
                                    END as credit,
                                    CASE WHEN tfl.line_type='receivable' THEN amount
                                    ELSE 0.0
                                    END as debit,
                                    CASE WHEN tfl.line_type='receivable' THEN amount
                                    ELSE -amount
                                    END as balance,
                                    payment_mode_id,
                                    CASE WHEN tfl.line_type='receivable' THEN 'in'
                                    ELSE 'out'
                                    END as type,
                                    tfl.partner_id
                                from    account_treasury_forecast tf 
                                    inner join account_treasury_forecast_line tfl on tf.id = tfl.treasury_id
                                union
                                select
                                    tcf.id || 'c' AS id,
                                    tcf.id as id_ref,
                                    tcf.name as concept,
                                    treasury_id,
                                    tcf.date as date,
                                    CASE WHEN tcf.flow_type='in' THEN 0.0
                                    ELSE abs(amount)
                                    END as credit,
                                    CASE WHEN tcf.flow_type='in' THEN amount
                                    ELSE 0.0
                                    END as debit,
                                    amount as balance,
                                    payment_mode_id,
                                    flow_type as type,
                                    null as partner_id
                                from    account_treasury_forecast tf 
                                    inner join account_treasury_forecast_cashflow tcf on tf.id = tcf.treasury_id
                                union
                                select
                                    tfii.id || 'i' AS id,
                                    ai.id as id_ref, 
                                    ai.number as concept,
                                    treasury_id,
                                    tfii.date_due as date,
                                    CASE WHEN ai.type='in_invoice' THEN tfii.total_amount
                                    ELSE 0.0
                                    END as credit,
                                    CASE WHEN ai.type='in_invoice' THEN 0.0
                                    ELSE tfii.total_amount
                                    END as debit,
                                    CASE WHEN ai.type='in_invoice' THEN -tfii.total_amount
                                    ELSE tfii.total_amount
                                    END as balance,
                                    tfii.payment_mode_id,
                                    CASE WHEN ai.type='in_invoice' THEN 'out'
                                    ELSE 'in'
                                    END as type,
                                    tfii.partner_id
                                    from
                                    account_treasury_forecast tf 
                                    inner join account_treasury_forecast_in_invoice_rel tfiir on tf.id = tfiir.treasury_id 
                                    inner join account_treasury_forecast_invoice tfii on tfii.id = tfiir.in_invoice_id 
                                    inner join account_invoice ai on ai.id = tfii.invoice_id
                                union
                                select
                                    tfio.id || 'o' AS id,
                                    ai.id as id_ref, 
                                    ai.number as concept,
                                    treasury_id,
                                    tfio.date_due as date,
                                    CASE WHEN ai.type='out_invoice' THEN 0.0
                                    ELSE tfio.total_amount
                                    END as credit,
                                    CASE WHEN ai.type='out_invoice' THEN tfio.total_amount
                                    ELSE 0.0
                                    END as debit,
                                    CASE WHEN ai.type='out_invoice' THEN tfio.total_amount
                                    ELSE -tfio.total_amount
                                    END as balance,
                                    tfio.payment_mode_id,
                                    CASE WHEN ai.type='out_invoice' THEN 'in'
                                    ELSE 'out'
                                    END as type,
                                    tfio.partner_id
                                from    account_treasury_forecast tf 
                                    inner join account_treasury_forecast_out_invoice_rel tfior on tf.id = tfior.treasury_id 
                                    inner join account_treasury_forecast_invoice tfio on tfio.id = tfior.out_invoice_id 
                                    inner join account_invoice ai on ai.id = tfio.invoice_id
                            ) analysis
                            LEFT JOIN res_partner rp ON rp.id = analysis.partner_id
                            LEFT JOIN payment_mode pm ON pm.id = analysis.payment_mode_id
                            ORDER  BY analysis.treasury_id, analysis.date, analysis.id_ref
            )""")

