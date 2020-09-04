##############################################################################
#
#    Copyright (C) 2015 Comunitea Servicios Tecnológicos All Rights Reserved
#    $Omar Castiñeira Saavedra <omar@pcomunitea.com>$
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
from odoo.exceptions import Warning
#TODO: (Ahora es account_credit_control) from openerp.addons.account_followup.report import account_followup_print
from collections import defaultdict
import time
from datetime import date
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
import dateutil.relativedelta,re
from calendar import monthrange
from odoo.addons.phone_validation.tools import phone_validation


class ResPartnerInvoiceType(models.Model):
    _name = 'res.partner.invoice.type'

    name = fields.Char("Name", required=True)


class PhoneValidationMixin(models.AbstractModel):
    _inherit = 'phone.validation.mixin'

    def phone_format(self, number, country=None, company=None):
        country = country or self._phone_get_country()
        if not country:
            return number
        always_international = company.phone_international_format == 'prefix' if company else self._phone_get_always_international()
        return phone_validation.phone_format(
            number,
            country.code if country else None,
            country.phone_code if country else None,
            always_international=always_international,
            # We only change this parameter to raise the exception
            raise_exception=True
        )


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _search_pricelist_name(self, operator, operand):
        pricelists = self.env['product.pricelist'].\
            search([('name', operator, operand)])
        if pricelists:
            field = self.env['ir.model.fields'].\
                search([('name', '=', 'property_product_pricelist'),
                        ('model', '=', 'res.partner')], limit=1)
            properties = self.env['ir.property'].\
                search([('fields_id', '=', field.id),
                        ('value_reference', 'in',
                         ['product.pricelist,' + str(x.id) for
                          x in pricelists]), ('res_id', '!=', False)])
            partners = self.env['res.partner'].search(
                [('id', 'in',
                  [int(x.res_id.split(',')[1]) for x in properties])])
            return [('id', 'in', partners.ids)]
        return [('id', '=', False)]

    annual_invoiced = fields.Float("Annual invoiced", readonly=True, store=True, default=0.0)
    past_year_invoiced = fields.Float("Past year invoiced", readonly=True, store=True, default=0.0)
    monthly_invoiced = fields.Float("Monthly invoiced", readonly=True, store=True, default=0.0)
    past_month_invoiced = fields.Float("Past Month invoiced", readonly=True, store=True, default=0.0)
    current_global_invoiced = fields.Float("Current year invoiced (global)", default=0.0)
    past_year_global_invoiced = fields.Float("Past year invoiced (global)", default=0.0)
    current_employees = fields.Integer("Current year employees", default=0)
    past_year_employees = fields.Integer("Past year employees", default=0)
    ref_supplier = fields.Char("Ref. Supplier", size=3)
    property_product_pricelist = fields.\
        Many2one(search="_search_pricelist_name")


    @api.model
    def _calculate_annual_invoiced(self):
        partner_obj = self.env['res.partner']
        invoice_obj = self.env['account.invoice']
        order_obj = self.env['sale.order.line']
        partner_ids = partner_obj.search([('is_company', '=', True),
                                          ('child_ids', '!=', False),
                                          ('customer', '=', True)])
        actual_date = datetime.now()
        actual_year = actual_date.year
        past_month = actual_date - relativedelta(months=1)
        past_month_year = past_month.year
        past_month = past_month.month
        past_year = actual_date - relativedelta(years=1)
        past_year = past_year.year
        actual_month = actual_date.month
        actual_day = actual_date.day
        start_year = str(actual_year) + '-01-01'
        start_past_year = str(past_year) + '-01-01'
        start_month = str(actual_year) + '-' + str(actual_month) + '-01'
        start_past_month = str(past_month_year) + '-' + str(past_month) + '-01'
        end_year = str(actual_year) + '-12-31'
        end_past_year = str(past_year) + '-12-31'
        end_month = str(actual_year) + '-' + str(actual_month) + '-' + str(actual_day)
        end_day_past_month = monthrange(past_month_year, past_month)
        end_past_month = str(past_month_year) + '-' + str(past_month) + '-' + str(end_day_past_month[1])
        for partner in partner_ids:
            invoice_ids_year = invoice_obj.search_read([('date_invoice', '>=', start_year),
                                                        ('date_invoice', '<=', end_year),
                                                        ('partner_id', 'child_of', [partner.id]),
                                                        ('type', 'in', ['out_invoice', 'out_refund']),
                                                        ('number', 'not like', '%_ef%'),
                                                        '|',
                                                        ('state', '=', 'open'),
                                                        ('state', '=', 'paid')], ['type', 'amount_untaxed'])

            invoice_ids_past_year = invoice_obj.search_read([('date_invoice', '>=', start_past_year),
                                                             ('date_invoice', '<=', end_past_year),
                                                             ('partner_id', 'child_of', [partner.id]),
                                                             ('type', 'in', ['out_invoice', 'out_refund']),
                                                             ('number', 'not like', '%_ef%'),
                                                             '|',
                                                             '|',
                                                             ('state', '=', 'open'),
                                                             ('state', '=', 'paid'),
                                                             ('state', '=', 'history')], ['type', 'amount_untaxed'])

            invoice_ids_month = invoice_obj.search_read([('date_invoice', '>=', start_month),
                                                         ('date_invoice', '<=', end_month),
                                                         ('partner_id', 'child_of', [partner.id]),
                                                         ('type', 'in', ['out_invoice', 'out_refund']),
                                                         ('number', 'not like', '%_ef%'),
                                                         '|',
                                                         ('state', '=', 'open'),
                                                         ('state', '=', 'paid')], ['type', 'amount_untaxed'])

            invoice_ids_past_month = invoice_obj.search_read([('date_invoice', '>=', start_past_month),
                                                              ('date_invoice', '<=', end_past_month),
                                                              ('partner_id', 'child_of', [partner.id]),
                                                              ('type', 'in', ['out_invoice', 'out_refund']),
                                                              ('number', 'not like', '%_ef%'),
                                                              '|',
                                                              ('state', '=', 'open'),
                                                              ('state', '=', 'paid')], ['type', 'amount_untaxed'])

            o_lines = order_obj.search([('order_id.partner_id', 'child_of', [partner.id]),
                                        ('order_id.state', '=', 'sale'),
                                        ('qty_delivered', '>', 0)]).filtered(lambda l: l.qty_delivered > l.qty_invoiced)

            order_lines_year = o_lines.filtered(lambda l: start_year <= l.order_id.date_order <= end_year)
            order_lines_past_year = o_lines.filtered(lambda l: start_past_year <= l.order_id.date_order <= end_year)
            order_lines_month = o_lines.filtered(lambda l: start_month <= l.order_id.date_order <= end_month)
            order_lines_past_month = o_lines.filtered(lambda l: start_past_month <= l.order_id.date_order <= end_past_month)

            annual_invoiced = 0.0
            past_year_invoiced = 0.0
            monthly_invoiced = 0.0
            past_month_invoiced = 0.0

            for invoice in invoice_ids_year:
                if invoice['type'] == 'out_refund':
                    annual_invoiced -= invoice['amount_untaxed']
                else:
                    annual_invoiced += invoice['amount_untaxed']

            for invoice in invoice_ids_month:
                if invoice['type'] == 'out_refund':
                    monthly_invoiced -= invoice['amount_untaxed']
                else:
                    monthly_invoiced += invoice['amount_untaxed']

            for invoice in invoice_ids_past_year:
                if invoice['type'] == 'out_refund':
                    past_year_invoiced -= invoice['amount_untaxed']
                else:
                    past_year_invoiced += invoice['amount_untaxed']

            for invoice in invoice_ids_past_month:
                if invoice['type'] == 'out_refund':
                    past_month_invoiced -= invoice['amount_untaxed']
                else:
                    past_month_invoiced += invoice['amount_untaxed']

            annual_invoiced += sum(order_lines_year.mapped('price_subtotal'))
            past_year_invoiced += sum(order_lines_past_year.mapped('price_subtotal'))
            monthly_invoiced += sum(order_lines_month.mapped('price_subtotal'))
            past_month_invoiced += sum(order_lines_past_month.mapped('price_subtotal'))

            vals = {'annual_invoiced': annual_invoiced, 'past_year_invoiced': past_year_invoiced,
                    'monthly_invoiced': monthly_invoiced, 'past_month_invoiced': past_month_invoiced}
            partner.write(vals)

    # TODO -> Migrar: depende de custom_account (Revisar si se sigue utilizando el cron o no)
    """ @api.model
    def _unblock_invoices(self):
        date_limit = date.today() - timedelta(days=7)
        payment_term_ids = self.env['account.payment.term'].search([('blocked', '=', 'True')])
        partner_ids = self.env['res.partner'].search([('prnot_print_pickingoperty_payment_term_id', 'in', payment_term_ids.ids)])
        invoice_ids = self.env['account.invoice'].search([('date_due', '<=', date_limit),
                                                          ('state', '=', 'open'),
                                                          ('partner_id', 'child_of', partner_ids.ids),
                                                          ('number', 'not like', '%_ef%'),
                                                          ('number', 'not like', 'VEN%')])
        move_line_obj = self.env['account.move.line']
        move_ids = move_line_obj.search([('stored_invoice_id', 'in', invoice_ids.ids),
                                         ('debit', '!=', '0')])
        val = {'blocked': False}
        move_ids.write(val)
    """

    @api.multi
    def _purchase_invoice_count(self):
        invoice = self.env['account.invoice']
        for partner in self:
            partner.supplier_all_invoice_count = invoice.search_count([('partner_id', 'child_of', partner.id),
                                                                       '|', ('type', '=', 'in_invoice'),
                                                                       ('type', '=', 'in_refund')])

    @api.multi
    def _invoice_total_real(self):
        context = self.env.context
        account_invoice_report = self.env['account.invoice.report']
        user = self.env['res.users'].browse(self.env.uid)
        user_currency_id = user.company_id.currency_id.id
        for partner_id in self:
            all_partner_ids = self.search([('id', 'child_of', partner_id.id)])
            # searching account.invoice.report via the orm is comparatively expensive
            # (generates queries "id in []" forcing to build the full table).
            # In simple cases where all invoices are in the same currency than the user's company
            # access directly these elements
            domain = [('partner_id', 'in', all_partner_ids.ids),
                      ('state', 'not in', ['draft', 'cancel'])
                      # TODO -> Migrar: depende de custom_account
                      # Error: Invalid field 'number' on account_invoice_report
                      #  ,('number', 'not like', '%_ef%')
                      ]
            if context.get('date_from', False):
                domain.append(('date', '>=', context['date_from']))
            # generate where clause to include multicompany rules
            where_query = account_invoice_report._where_calc(domain)
            account_invoice_report._apply_ir_rules(where_query, 'read')
            from_clause, where_clause, where_clause_params = where_query.get_sql()

            query = """ WITH currency_rate (currency_id, rate, date_start, date_end) AS (
                                SELECT r.currency_id, r.rate, r.name AS date_start,
                                    (SELECT name FROM res_currency_rate r2
                                     WHERE r2.name > r.name AND
                                           r2.currency_id = r.currency_id
                                     ORDER BY r2.name ASC
                                     LIMIT 1) AS date_end
                                FROM res_currency_rate r
                                )
                      SELECT SUM(price_total * cr.rate) as total
                        FROM account_invoice_report account_invoice_report, currency_rate cr
                       WHERE %s
                         AND cr.currency_id = %%s
                         AND (COALESCE(account_invoice_report.date, NOW()) >= cr.date_start)
                         AND (COALESCE(account_invoice_report.date, NOW()) < cr.date_end OR cr.date_end IS NULL)
                    """ % where_clause

            # price_total is in the currency with rate = 1
            # total_invoice should be displayed in the current user's currency
            self.env.cr.execute(query, where_clause_params + [user_currency_id])
            partner_id.total_invoiced_real = self.env.cr.fetchone()[0]

    total_invoiced_real = fields.Float(compute='_invoice_total_real', string="Total Invoiced",
                                       groups='account.group_account_invoice')
    supplier_all_invoice_count = fields.Integer(compute='_purchase_invoice_count', string="# Supplier Invoices")

    @api.multi
    def _get_products_sold(self):
        for partner in self:
            lines = self.env['sale.order.line'].read_group([('order_partner_id', '=', partner.id)],
                                                           ['product_id'],
                                                           groupby="product_id")
            partner.sale_product_count = len(lines)

    @api.multi
    def _sale_order_count(self):
        for partner in self:
            partner.sale_order_count = len(self.env["sale.order"].
                                           search([('partner_id', 'child_of', [partner.id]),
                                                   ('state', 'not in', ['draft', 'cancel', 'sent'])]))

    @api.multi
    def _get_growth_rate(self):
        # TODO -> Probar cuando se calcule bien total_invoiced_real
        for partner in self:
            if partner.customer:
                search_date_180 = (date.today() - relativedelta(days=180)).strftime("%Y-%m-%d")
                invoiced_180 = partner.with_context(date_from=search_date_180).browse(partner.id).total_invoiced_real
                diary_invoice = invoiced_180 / 180.0
                goal = diary_invoice * 15.0
                if goal:
                    search_date_15 = (date.today() - relativedelta(days=15)).strftime("%Y-%m-%d")
                    invoiced_15 = partner.with_context(date_from=search_date_15).browse(partner.id).total_invoiced_real
                    partner.growth_rate = invoiced_15 / goal

    @api.multi
    def _get_average_margin(self):
        for partner in self:
            if partner.customer:
                margin_avg = 0.0
                total_price = 0.0
                total_cost = 0.0

                d1 = datetime.strptime(datetime.now().strftime("%Y-%m-%d"), "%Y-%m-%d")
                final_date = d1.strftime("%Y-%m-%d")
                d2 = d1 - dateutil.relativedelta.relativedelta(months=3)
                start_date = d2.strftime("%Y-%m-%d")

                invoices = self.env['account.invoice'].search(
                    [('commercial_partner_id', '=', partner.id),
                     ('number', 'not like', '%_ef%'),
                     ('state', 'in', ['paid', 'history', 'open']),
                     ('date_invoice', '>=', start_date),
                     ('date_invoice', '<=', final_date)])

                for i_line in invoices.mapped('invoice_line_ids'):
                    if i_line.sale_line_ids:
                        total_price += i_line.quantity * i_line.price_unit * ((100.0 - i_line.discount) / 100)
                        total_cost += i_line.quantity * i_line.cost_unit

                if total_price:
                    margin_avg = (1 - total_cost / total_price) * 100.0

                partner.average_margin = margin_avg



    web = fields.Boolean("Web", help="Created from web", copy=False)
    email_web = fields.Char("Email Web")
    sale_product_count = fields.Integer(compute='_get_products_sold',
                                        string="# Products sold",
                                        readonly=True)
    sale_order_count = fields.Integer(compute='_sale_order_count',
                                      string='# of Sales Order')
    invoice_type_id = fields.Many2one('res.partner.invoice.type',
                                      'Invoice type')
    dropship = fields.Boolean("Dropship")
    send_followup_to_user = fields.Boolean("Send followup to sales agent")
    notified_creditoycaucion = fields.Date("Notified to Crédito y Caución")
    is_accounting = fields.Boolean("Is Acounting", compute='_is_accounting')
    eur_currency = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.EUR'))
    purchase_quantity = fields.Float("", compute='_get_purchased_quantity')
    att = fields.Char("A/A")
    growth_rate = fields.Float("Growth rate", readonly=True, compute='_get_growth_rate')
    average_margin = fields.Float("Average Margin", readonly=True, compute='_get_average_margin')

    unreconciled_purchase_aml_ids = fields.One2many('account.move.line', 'partner_id',
                                                    domain=[('full_reconcile_id', '=', False),
                                                            ('account_id.internal_type', '=', 'payable'),
                                                            ('move_id.state', '!=', 'draft')])
    created_by_web = fields.Boolean("Created by web", default=lambda self: self.env['ir.config_parameter'].sudo().get_param('web.user.buyer') == self.env.user.login)

    @api.model
    def _commercial_fields(self):
        res = super()._commercial_fields()
        return res + ['web']

    @api.multi
    def _is_accounting(self):
        accountant = self.env.ref('account.group_account_manager')
        is_accountant = self.env.user.id in accountant.users.ids
        if is_accountant:
            for partner in self:
                partner.is_accounting = True
        else:
            for partner in self:
                partner.is_accounting = False

    @api.multi
    def _get_purchased_quantity(self):
        for partner in self:
            lines = self.env['purchase.order.line'].search(
                [('order_id.state', '=', 'approved'),
                 ('order_id.partner_id', '=', partner.id),
                 ('qty_received', '>', 0)]).filtered(lambda l: l.qty_received > l.qty_invoiced)
            purchases = self.env['purchase.order'].search([('id', 'in', lines.mapped('order_id.id'))])
            total = sum(purchases.mapped('amount_total'))
            partner.purchase_quantity = total

    @api.multi
    @api.constrains('email_web')
    def check_unique_email_web(self):
        for partner in self:
            if partner.email_web and partner.is_company:
                # Solo comprobamos para compañías, ya que se arrastra a contactos.
                ids = self.search(
                    [('email_web', '=ilike', partner.email_web),
                     ('id', '!=', partner.id), ('is_company', '=', True)])
                if ids:
                    raise exceptions.ValidationError(_('Email web must be unique'))

    @api.multi
    @api.constrains('ref', 'is_company', 'active')
    def check_unique_ref(self):
        for partner in self:
            if partner.is_company and partner.active:
                ids = self.search([('ref', '=', partner.ref),
                                   ('is_company', '=', True),
                                   ('id', '!=', partner.id)])
                if ids:
                    raise exceptions. \
                        ValidationError(_('Partner ref must be unique'))

    @api.multi
    @api.constrains('child_ids', 'is_company', 'active')
    def check_unique_child_ids(self):
        for partner in self:
            if partner._context.get('install_mode'):
                return
            if partner.is_company and partner.active:
                if not partner.child_ids:
                    raise exceptions. \
                        ValidationError(_('At least, a contact must be added'))

    @api.multi
    @api.constrains('vat', 'is_company', 'supplier', 'customer', 'active')
    def check_unique_vat(self):
        for partner in self:
            if partner._context.get('install_mode'):
                return
            if partner.is_company and partner.active:
                ids = self.search([('vat', '=', partner.vat),
                                   ('is_company', '=', True),
                                   ('id', '!=', partner.id),
                                   ('supplier', '=', partner.supplier),
                                   ('customer', '=', partner.customer)])
                if ids:
                    raise exceptions. \
                        ValidationError(_('VAT must be unique'))

    def check_email(self, email):
        any_char="^\s\t\r\n\(\)\<\>\,\:\;\[\]Çç\%\&@á-źÁ-Ź"
        return not re.match('^(['+any_char+']+@['+any_char+'\.]+(\.['+any_char+'\.]+)+;?)+$', email) and email!="-" and email!="."

    @api.constrains('email', 'email2', 'email_web')
    def check_emails(self):
        email = self.email
        email2 = self.email2
        email_web = self.email_web
        message = _('[Partner "%s"] The e-mail format is incorrect: ') %self.name
        if email:
            not_correct = self.check_email(email)
            if not_correct:
                message += ' "%s" (Email)' % email
                raise exceptions.ValidationError(message)
        if email2:
            not_correct = self.check_email(email2)
            if not_correct:
                message += _(' "%s" (Accounting email)') % email2
                raise exceptions.ValidationError(message)
        if email_web:
            not_correct = self.check_email(email_web)
            if not_correct:
                message += ' "%s" (Email Web)' % email_web
                raise exceptions.ValidationError(message)
    @api.multi
    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if record.parent_id and not record.is_company and not record.dropship:
                name = "{0}, {1}".format(record.parent_name, name)
            if self.env.context.get('show_address_only'):
                name = record._display_address(without_company=True)
            if self.env.context.get('show_address'):
                name = name + "\n" + record._display_address(without_company=True)
            name = name.replace('\n\n', '\n')
            name = name.replace('\n\n', '\n')
            if self.env.context.get('show_email') and record.email:
                name = "{0} <{1}>".format(name, record.email)
            res.append((record.id, name))
        return res

    @api.model
    def create(self, vals):
        if vals.get('dropship', False):
            vals['active'] = False
        if 'web' in vals and not vals['web']:
            vals['email_web'] = None
        vals['date'] = fields.Date.today()
        return super(ResPartner, self).create(vals)

    @api.multi
    @api.constrains('child_ids')
    def check_default_shipping_child(self):
        vals_dict = {}
        for child in self.child_ids:
            if child.default_shipping_address:
                if 'True' in vals_dict:
                    raise Warning('Dos o mas direcciones marcadas como predeterminadas')
                else:
                    vals_dict[str(child.default_shipping_address)] = child.id

    @api.multi
    def write(self, vals):
        if vals.get('dropship', False):
            vals['active'] = False
        if 'web' in vals and not vals['web']:
            vals['email_web'] = None
        for partner in self:
            if not partner.active and 'active' in vals:
                if vals['active']:
                    partner.message_post(body=_("Prospective customer becomes an active customer"))
        res = super(ResPartner, self).write(vals)
        if 'lang' in vals and not vals.get('lang', False):
            for partner in self:
                if partner.parent_id and partner.lang != partner.parent_id.lang:
                    partner.lang = partner.parent_id.lang
        return res

    # TODO: Migrar -> depende de credit_control (?)
    """def _all_lines_get_with_partner(self, cr, uid, partner, company_id, days):
        today = time.strftime('%Y-%m-%d')
        moveline_obj = self.pool['account.move.line']

        domain = [('partner_id', '=', partner.id),
                  ('account_id.internal_type', '=', 'receivable'),
                  ('full_reconcile_id', '=', False),
                  ('move_id.state', '!=', 'draft'),
                  ('company_id', '=', company_id),
                  ('date_maturity', '>', today)]
        if days:
            formatted_date = datetime.strptime(today, "%Y-%m-%d")
            due_date = datetime. \
                strftime(formatted_date + timedelta(days=days), "%Y-%m-%d")
            domain.append(('date_maturity', '<=', due_date))

        moveline_ids = moveline_obj.search(cr, uid, domain)

        # lines_per_currency = {currency: [line data, ...], ...}
        lines_per_currency = defaultdict(list)
        for line in moveline_obj.browse(cr, uid, moveline_ids):
            currency = line.currency_id or line.company_id.currency_id
            invoice_obj = self.pool['account.invoice']
            if line.stored_invoice_id:
                invoice = invoice_obj.browse(cr, uid, line.stored_invoice_id[0].id)
                client_order_ref = invoice.invoice_line_ids[0].move_id.procurement_id.sale_line_id.order_id.client_order_ref
                if not client_order_ref:
                    client_order_ref = ""
            else:
                client_order_ref = ""

            line_data = {
                'name': line.move_id.name,
                'ref': line.ref,
                'date': line.date,
                'date_maturity': line.date_maturity,
                'balance': line.amount_currency if currency != line.company_id.currency_id else line.debit - line.credit,
                'blocked': line.blocked,
                'currency_id': currency,
                'client_order_ref': client_order_ref,
            }
            lines_per_currency[currency].append(line_data)

        return [{'line': lines, 'currency': currency} for currency, lines in lines_per_currency.items()]

    def get_not_followup_table_html(self, cr, uid, ids, days=0, context=None):
        assert len(ids) == 1
        if context is None:
            context = {}
        partner = self.browse(cr, uid, ids[0], context=context).commercial_partner_id
        # copy the context to not change global context. Overwrite it because _() looks for the lang in local variable 'context'.
        # Set the language to use = the partner language
        context = dict(context, lang=partner.lang)
        followup_table = ''
        if partner.unreconciled_aml_ids:
            company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
            current_date = fields.Date.today()
            rml_parse = account_followup_print.report_rappel(cr, uid, "followup_rml_parser")
            final_res = self._all_lines_get_with_partner(cr, uid, partner, company.id, days=days)

            for currency_dict in final_res:
                currency = currency_dict.get('line', [{'currency_id': company.currency_id}])[0]['currency_id']
                followup_table += '''
                <table border="2" width=100%%>
                <tr>
                    <td>''' + _("Invoice Date") + '''</td>
                    <td>''' + _("Invoice No.") + '''</td>
                    <td>''' + _("Client Order Ref.") + '''</td>
                    <td>''' + _("Due Date") + '''</td>
                    <td>''' + _("Amount") + " (%s)" % (currency.symbol) + '''</td>
                </tr>
                '''
                total = 0
                for aml in currency_dict['line']:
                    block = aml['blocked'] and 'X' or ' '
                    total += aml['balance']
                    strbegin = "<TD>"
                    strend = "</TD>"
                    date = aml['date_maturity'] or aml['date']
                    followup_table += "<TR>" + strbegin + str(aml['date']) + strend +\
                                      strbegin + (aml['ref'] or '') + strend +\
                                      strbegin + (aml['client_order_ref'] or '') + strend +\
                                      strbegin + str(date) + strend + strbegin +\
                                      str(aml['balance']) + strend + "</TR>"

                total = reduce(lambda x, y: x + y['balance'], currency_dict['line'], 0.00)

                total = rml_parse.formatLang(total, dp='Account', currency_obj=currency)
                followup_table += '''<tr> </tr>
                                </table>
                                <strong><center style="font-size: 18px">''' + _("Amount not due") +\
                                  ''' : %s </center></strong>''' % (total)
        return followup_table

        def get_custom_followup_table_html(self, cr, uid, ids, context=None):
        ''' Build the html tables to be included in emails send to partners,
            when reminding them their overdue invoices.
            :param ids: [id] of the partner for whom we are building the tables
            :rtype: string
        '''
        assert len(ids) == 1
        if context is None:
            context = {}
        partner = self.browse(cr, uid, ids[0], context=context).commercial_partner_id
        #copy the context to not change global context. Overwrite it because _() looks for the lang in local variable 'context'.
        #Set the language to use = the partner language
        context = dict(context, lang=partner.lang)
        followup_table = ''
        if partner.unreconciled_aml_ids:
            company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
            current_date = fields.Date.today()
            rml_parse = account_followup_print.report_rappel(cr, uid, "followup_rml_parser")
            final_res = rml_parse._lines_get_with_partner(partner, company.id)

            for currency_dict in final_res:
                currency = currency_dict.get('line', [{'currency_id': company.currency_id}])[0]['currency_id']
                followup_table += '''
                <table border="2" width=100%%>
                <tr>
                    <td>''' + _("Invoice Date") + '''</td>
                    <td>''' + _("Invoice No.") + '''</td>
                    <td>''' + _("Client Order Ref.") + '''</td>
                    <td>''' + _("Due Date") + '''</td>
                    <td>''' + _("Amount") + " (%s)" % (currency.symbol) + '''</td>
                </tr>
                '''
                total = 0
                for aml in currency_dict['line']:
                    block = aml['blocked'] and 'X' or ' '
                    total += aml['balance']
                    strbegin = "<TD>"
                    strend = "</TD>"
                    date = aml['date_maturity'] or aml['date']
                    if date <= current_date and aml['balance'] > 0:
                        strbegin = "<TD><B>"
                        strend = "</B></TD>"
                    followup_table += "<TR>" + strbegin + str(aml['date']) + strend +\
                                      strbegin + (aml['ref'] or '') + strend +\
                                      strbegin + (aml['client_order_ref'] or '') + strend +\
                                      strbegin + str(date) + strend +\
                                      strbegin + str(aml['balance']) + strend + "</TR>"

                total = reduce(lambda x, y: x+y['balance'], currency_dict['line'], 0.00)

                total = rml_parse.formatLang(total, dp='Account', currency_obj=currency)
                followup_table += '''<tr> </tr>
                                </table>
                                <strong> <center style="font-size: 18px">''' + _("Amount due") \
                                  + ''' : %s </center> </strong>''' % (total)
        return followup_table"""

    @api.multi
    @api.onchange('dropship')
    def onchange_dropship(self):
        if self.dropship:
            res = {'warning': {
                'title': _('Warning'),
                'message': _('Remember to set our partner email, not dropship email!')
            }}
            if res:
                return res

    @api.multi
    @api.onchange('vat')
    def onchange_vat_country_completion(self):
        country_code = self.commercial_partner_id.country_id.code
        if country_code and self.vat and self.is_company:
            if self.vat[:len(country_code)] != country_code:
                self.vat = country_code + self.vat

    @api.multi
    def open_partner(self):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        record_url = base_url + '/web/?#id=' + str(self.id) + '&view_type=form&model=res.partner'
        return {
            'type': 'ir.actions.act_url',
            'view_type': 'form',
            'url': record_url,
            'target': 'new'
        }

    @api.multi
    def call_new_window(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        order_view_id = self.env.ref('custom_partner.crm_case_categ_phone_incoming3').id
        record_url = base_url + '/web?#page=0&limit=80&view_type=list&model=crm.phonecall&action=' \
                              + str(order_view_id) + '&active_id=' + str(self.id)
        return {
            'name': 'Phone Calls',
            'view_type': 'tree',
            'type': 'ir.actions.act_url',
            'url': record_url,
            'context': self.env.context,
            'target': 'new',
            }

    @api.multi
    @api.depends('company_credit_limit', 'insurance_credit_limit','fidelity_credit_limit','fidelity_credit_limit_include')
    def _compute_credit_limit(self):
        res = super(ResPartner, self)._compute_credit_limit()
        partners = self.filtered(lambda p: p.fidelity_credit_limit_include)
        for partner in partners:
            partner.credit_limit += partner.fidelity_credit_limit
        return res

    def _calculate_fidelity_credit_limit(self):
        partners = self.env['res.partner'].search([('parent_id','=',False),('customer','=',True),('fidelity_credit_limit_include', '=', True)])
        partners.compute_fidelity_credit_limit()

    @api.multi
    @api.depends('fidelity_credit_limit_include')
    def compute_fidelity_credit_limit(self):
        """This function calculates the field fidelity_credit_limit.
        Only open and unexpired, or paid invoices will be used for its calculation.
        Fidelity_credit_limit will be the sum of the benefit of the invoice lines
        whose invoice type is "out_invoice" - the sum of the benefit of the invoice lines
        whose invoice type is "out_refund"
        If total benefit of last x months(the variable x is determined by the system
        parameter "benefit.months") is lower than 0, the value of this field will be 0 """
        months = int(self.env['ir.config_parameter'].sudo().get_param('benefit.months'))
        d1 = datetime.strptime(datetime.now().strftime("%Y-%m-%d"), "%Y-%m-%d")
        date_end = d1.strftime("%Y-%m-%d")
        d2 = d1 - dateutil.relativedelta.relativedelta(months=months)
        date_start = d2.strftime("%Y-%m-%d")
        for partner in self:
            benefit = 0
            if partner.fidelity_credit_limit_include:
                invoice_lines = partner.env['account.invoice'].search(
                    ['&', '&', '&',
                     ('date_invoice', '>=', date_start), ('date_invoice', '<=', date_end), '&',
                     ('partner_id', 'child_of', [partner.id]),
                     ('type', 'in', ['out_invoice', 'out_refund']), '|',
                     ('state', '=', 'paid'), '&',('state', '=', 'open'), ('date_due', '>=', date_end)]).mapped(
                    'invoice_line_ids')
                for line in invoice_lines:
                    if line.invoice_id.type == 'out_invoice':
                        benefit += line.quantity * line.price_unit * (100.0 - line.discount) / 100.0 - (
                            line.cost_unit if line.cost_unit else 0) * line.quantity
                    else:
                        benefit -= line.quantity * line.price_unit * (100.0 - line.discount) / 100.0 - (
                            line.cost_unit if line.cost_unit else 0) * line.quantity

            partner.fidelity_credit_limit = benefit if benefit >= 0 else 0

    fidelity_credit_limit = fields.Float("Fidelity Credit Limit",
                                        help='Profit of the last x months' ,compute="compute_fidelity_credit_limit", store=True)
    fidelity_credit_limit_include = fields.Boolean("Include fidelity credit limit",
                                                   help="If this field is checked, the fidelity credit limit will be added to credit limit ")
    mail_count = fields.Integer(compute="_compute_mail_count")

    @api.multi
    @api.depends('email')
    def _compute_mail_count(self):
        for partner in self:
            domain_to=[]
            if partner.email and partner.email2:
                domain_to =['|',('email_to', 'in', [partner.email,partner.email2])]
            elif partner.email:
                domain_to = ['|',('email_to', '=', partner.email)]
            elif partner.email2:
                domain_to = ['|',('email_to', '=', partner.email2)]
            if domain_to:
                count = self.env['mail.mail'].search_count(domain_to+[('recipient_ids','in',[partner.id])])
            else:
                count = self.env['mail.mail'].search_count([('recipient_ids', 'in', [partner.id])])
            partner.mail_count = count

    def action_view_email(self):
        domain_to = []
        if self.email and self.email2:
            domain_to = ['|',('email_to', 'in', [self.email, self.email2])]
        elif self.email:
            domain_to = ['|',('email_to', '=', self.email)]
        elif self.email2:
            domain_to = ['|',('email_to', '=', self.email2)]
        mails = self.env['mail.mail'].search_read(domain_to+[('recipient_ids','in',[self.id])
                ],['id'])
        mail_ids = [x['id'] for x in mails]
        action = self.env.ref('custom_partner.action_view_emails').read()[0]
        if len(mail_ids) > 0:
            action['domain'] = [('id', 'in', mail_ids)]
            action['context'] = [('id', 'in', mail_ids)]
        return action


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    ref_line = fields.Char("Payment Reference", related='move_id.vref')
    residual_balance = fields.Float("Residual Balance", compute='_get_residual_balance')

    @api.multi
    def _get_residual_balance(self):
        for line in self:
            if line.amount_residual:
                line.residual_balance = line.amount_residual
            else:
                if line.balance < 0:
                    line.residual_balance = line.amount_residual
                else:
                    line.residual_balance = line.balance


class AccountMove(models.Model):
    _inherit = 'account.move'

    vref = fields.Char("Reference")


class AccountVoucher(models.Model):
    _inherit = 'account.voucher'

    @api.multi
    def account_move_get(self):
        move = super(AccountVoucher, self).account_move_get()
        move['vref'] = self.reference

        return move


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def _get_move_vals(self, journal=None):
        move = super()._get_move_vals(journal=journal)
        move['vref'] = self.communication or ''
        return move



class AccountPaymentOrder(models.Model):
    _inherit = 'account.payment.order'

    @api.multi
    def _prepare_move(self, bank_lines=None):
        vals = super()._prepare_move(bank_lines=bank_lines)
        vals['vref'] = self.description
        return vals

    @api.multi
    def _prepare_move_line_offsetting_account(
            self, amount_company_currency, amount_payment_currency,
            bank_lines):
        vals = super().\
            _prepare_move_line_offsetting_account(amount_company_currency,
                                                  amount_payment_currency,
                                                  bank_lines)
        journal = False
        if self.payment_mode_id.offsetting_account == 'bank_account':
            journal = self.journal_id
        elif self.payment_mode_id.offsetting_account == 'transfer_account':
            journal = self.payment_mode_id.transfer_journal_id
        if journal and ('RCONF' in journal.code or 'RPAG' in journal.code):
            vals['blocked'] = True

        return vals


class ProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    ref_supplier = fields.Char("Ref. Supplier", related='name.ref_supplier', readonly=True)


class Followers(models.Model):
    _inherit = 'mail.followers'

    @api.model
    def create(self, vals):
        if 'res_model' in vals and 'res_id' in vals and 'partner_id' in vals:
            dups = self.env['mail.followers'].search([('res_model', '=', vals.get('res_model')),
                                           ('res_id', '=', vals.get('res_id')),
                                           ('partner_id', '=', vals.get('partner_id'))])
            if len(dups):
                for p in dups:
                    p.sudo().unlink()
        return super(Followers, self).create(vals)
