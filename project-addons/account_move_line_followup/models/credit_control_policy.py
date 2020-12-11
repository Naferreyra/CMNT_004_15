# Copyright 2019 Omar Castiñeira, Comunitea Servicios Tecnológicos S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
import datetime


class CreditControlPolicy(models.Model):

    _inherit = "credit.control.policy"

    @api.multi
    def _move_lines_domain(self, controlling_date):
        """ Build the default domain for searching move lines """
        res = super()._move_lines_domain(controlling_date)
        res.append(('blocked', '!=', True))
        return res


class CreditControlPolicyLine(models.Model):

    _inherit = "credit.control.policy.level"

    channel = fields.Selection(selection_add=[('manual_action', 'Manual Action')])


class CreditControlLine(models.Model):

    _inherit = "credit.control.line"

    channel = fields.Selection(selection_add=[('manual_action', 'Manual Action')])

    @api.model
    def create(self, vals):
        line = super(CreditControlLine, self).create(vals)
        if line.channel == 'manual_action':
            line.manual_followup = True
        return line

    @api.multi
    def write(self, values):
        if 'manual_followup' in values:
            manual_followup_partner = self.partner_id.manual_followup
            res = super(CreditControlLine, self).write(values)
            # Put partner.manual_followup with the original value (do not update according to the credit line channel)
            # It will be updated in _generate_comm_from_credit_lines_custom function when necessary
            self.partner_id.manual_followup = manual_followup_partner
        else:
            res = super(CreditControlLine, self).write(values)
        return res


class CreditControlRun(models.Model):

    _inherit = "credit.control.run"

    @api.model
    def run_credit_control_cron(self):
        cron = self.create({'date': fields.Date.today()})
        cron.generate_credit_lines()
        cron.set_to_ready_lines()
        cron.run_channel_action_custom()

    @api.multi
    def run_channel_action_custom(self):
        self.ensure_one()
        lines = self.line_ids.filtered(lambda x: x.state == 'to_be_sent' and x.channel != 'letter')
        if lines:
            comm_obj = self.env['credit.control.communication']
            comms_email = comm_obj._generate_comm_from_credit_lines_custom(lines)
            for comm in comms_email:
                email = comm._generate_emails()
                # Associate communication_id to generated email
                email.write({'model': 'credit.control.communication',
                             'res_id': comm.id})
                # Send email
                email.send(auto_commit=True)


class CreditCommunication(models.Model):

    _name = 'credit.control.communication'
    _inherit = ['credit.control.communication', 'mail.thread']
    _order = 'report_date desc, id desc'

    move_line_ids = fields.Many2many('account.move.line', rel='comm_aml_rel', string="Account Move Lines")
    email_type = fields.Selection([
        ('automatic', 'Automatic email'),
        ('manual', 'Manual email')],
        "Email Type")

    @api.model
    def _clean_all_partner_followup(self):
        all_partner = self.env['res.partner'].search([('customer', '=', True), ('active', '=', True),
                                                      ('prospective', '=', False), ('is_company', '=', True),
                                                      ('parent_id', '=', False), ('child_ids', '!=', False),
                                                      ('latest_followup_level_id', '!=', False)])
        all_partner.write({'latest_followup_level_id': False})

    @api.model
    @api.returns('account.move.line')
    def _get_unreconciled_move_lines(self):
        """ Return unreconciled account move lines related to a partner """
        search_date = (fields.Date.from_string(fields.Date.today()) +
                       relativedelta(days=6)).strftime("%Y-%m-%d")
        move_line_obj = self.env['account.move.line']
        move_lines = move_line_obj.\
            search([('partner_id', '=', self.partner_id.id),
                    ('account_id.internal_type', '=', 'receivable'),
                    ('reconciled', '=', False),
                    ('move_id.state', '!=', 'draft'),
                    ('company_id', '=', self.company_id.id),
                    ('blocked', '!=', True),
                    '|', ('debit', '>', 0), ('credit', '>', 0),
                    '|', ('date_maturity', '=', False),
                    ('date_maturity', '<=', search_date)])
        return move_lines

    @api.model
    def _generate_comm_from_credit_lines_custom(self, lines):
        new_comms = self.browse()
        partner_obj = self.env['res.partner']
        policy_level_obj = self.env['credit.control.policy.level']

        self._clean_all_partner_followup()

        # Get the maximum level of all credit lines group by partner
        sql = (
            """ SELECT ccl.partner_id, ccl.policy_id, ccl.currency_id,
                       max(ccl.level) as level
                FROM credit_control_line ccl
                JOIN credit_control_policy_level ccpl ON ccpl.id = ccl.policy_level_id
                LEFT JOIN credit_control_policy_level ccpl_email ON ccpl_email.id = ccl.policy_level_id AND ccpl_email.channel = 'email'
                JOIN account_move_line aml ON aml.id = ccl.move_line_id
                WHERE ccl.id in %s AND COALESCE(aml.full_reconcile_id, 0) = 0
                GROUP BY ccl.partner_id, ccl.policy_id, ccl.currency_id

        """)
        cr = self.env.cr
        cr.execute(sql, (tuple(lines.ids), ))
        res = cr.dictfetchall()
        company_currency = self.env.user.company_id.currency_id

        for group in res:
            data = {}
            partner = partner_obj.browse([group['partner_id']])
            global_balance = partner.credit - partner.debit
            if global_balance >= 5 and not partner.not_send_following_email:
                # Maximum level partner
                partner_policy_level = policy_level_obj.search_read([('policy_id', '=', group['policy_id']),
                                                                     ('level', '=', group['level'])],
                                                                    ['id', 'channel'], limit=1)[0]
                send_email = True
                if partner_policy_level['channel'] == 'email' and partner.manual_followup:
                    # It probably means that last followup credit line was a manual level, but it's already reconciled
                    partner.manual_followup = False
                elif partner_policy_level['channel'] == 'manual_action':
                    send_email = False
                    partner.manual_followup = True

                partner_policy_level_id = partner_policy_level['id']
                # Update partner latest_followup_level_id to the new level communication
                partner.latest_followup_level_id = partner_policy_level_id

                if send_email:
                    data['partner_id'] = group['partner_id']
                    data['current_policy_level'] = partner_policy_level_id
                    data['currency_id'] = group['currency_id'] or company_currency.id
                    data['email_type'] = 'automatic'
                    comm = self.create(data)

                    move_lines = comm._get_unreconciled_move_lines()

                    balance = sum(move_lines.mapped('balance'))
                    if balance >= 5:
                        data['move_line_ids'] = [(6, 0, move_lines.ids)]
                        comm.write(data)
                        new_comms += comm
        return new_comms

    @api.multi
    def get_followup_table_html_base(self, moves):
        partner = self.partner_id.commercial_partner_id
        context = dict(self.env.context, lang=partner.lang)
        currency = self.company_id.currency_id
        followup_table = ''
        total = 0.0

        if moves:
            followup_table = '''
                  <table border="2" width=100%%>
                  <tr>
                      <td>''' + _("Invoice Date") + '''</td>
                      <td>''' + _("Invoice No.") + '''</td>
                      <td>''' + _("Due Date") + '''</td>
                      <td>''' + _("Amount") + " (%s)" % currency.symbol + '''</td>
                  </tr>
                  '''
            for aml in moves:
                # total += aml['balance']
                total += aml['amount_residual']
                strbegin = "<TD>"
                strend = "</TD>"
                date = aml['date_maturity'] or aml['date']
                if not aml.ref:
                    move_ref = aml.invoice_id and aml.invoice_id.number or ''
                else:
                    move_ref = aml.ref
                followup_table += "<TR>" + strbegin + datetime.datetime.strptime(aml['date'], '%Y-%m-%d').strftime('%d/%m/%Y') + strend + \
                                  strbegin + move_ref + strend + \
                                  strbegin + str(datetime.datetime.strptime(date, '%Y-%m-%d').strftime('%d/%m/%Y')) + strend + strbegin + \
                                  str(aml['amount_residual']) + strend + "</TR>"

        return followup_table, total

    @api.multi
    def get_followup_table_html_not_due(self):
        today = fields.Date.from_string(fields.Date.today()).strftime("%Y-%m-%d")
        aml_ids = self.move_line_ids.filtered(lambda l: l.invoice_id.state != 'paid')
        aml_not_due = aml_ids.filtered(lambda l: today < l.date_maturity)
        followup_table, total = self.get_followup_table_html_base(aml_not_due)
        if followup_table:
            followup_table += '''<tr> </tr>
                                       </table>
                                       <strong><center style="font-size: 18px">''' + _("Amount not due") + \
                              ''' : %s </center></strong>''' % (round(total, 2))
        return followup_table

    @api.multi
    def get_followup_table_html_due(self):
        today = fields.Date.from_string(fields.Date.today()).strftime("%Y-%m-%d")
        aml_ids = self.move_line_ids.filtered(lambda l: l.invoice_id.state != 'paid')
        aml_due = aml_ids.filtered(lambda l: today >= l.date_maturity)
        followup_table, total = self.get_followup_table_html_base(aml_due)
        if followup_table:
            followup_table += '''<tr> </tr>
                                       </table>
                                       <strong><center style="font-size: 18px">''' + _("Amount due") + \
                              ''' : %s </center></strong>''' % (round(total, 2))
        return followup_table

    @api.multi
    def get_email2(self):
        """ Return a valid accounting email for customer """
        self.ensure_one()
        partner = self.partner_id
        return partner.email2
