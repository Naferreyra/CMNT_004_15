
from odoo import models, api, fields
from datetime import datetime

class ResPartner(models.Model):

    _inherit = 'res.partner'

    worst_cyc_notify_date = fields.Date("Worst C&C notify date")


class AccountMoveLine(models.Model):

    _inherit = 'account.move.line'

    @api.model
    def cron_update_date_followup(self):
        # Searching negative account move line
        refund_aml = self.search([('full_reconcile_id', '=', False), ('account_id', '=', 443), ('credit', '!=', 0)])
        today = datetime.now().strftime("%Y-%m-%d")

        for aml in refund_aml:
            # Searching the most unfavorable maturity date on positive payments
            aml_partner = self.search_read([('partner_id', '=', aml.partner_id.id),
                                            ('full_reconcile_id', '=', False),
                                            ('account_id', '=', 443),
                                            ('debit', '!=', 0)],
                                           ['date_maturity'],
                                           limit=1, order="date_maturity asc")
            # Updating maturity date and follow-up data
            if aml_partner:
                aml_partner_data = aml_partner[0]
                if aml.date_maturity < aml_partner_data['date_maturity']:
                    aml.write({'date_maturity': aml_partner_data['date_maturity']})
            else:
                aml.write({'date_maturity': today})

        # Search all partner to update new field 'worst cyc notify date'
        all_partner = self.env['res.partner'].search([('customer', '=', True), ('active', '=', True),
                                                      ('prospective', '=', False), ('is_company', '=', True),
                                                      ('parent_id', '=', False), ('child_ids', '!=', False)])

        # Searching all positive account move line with cyc notify date
        aml_notify_date = self.search_read([('reconciled', '=', False),
                                            ('account_id', '=', 443),
                                            ('debit', '!=', 0),
                                            ('cyc_notify_date', '!=', False)],
                                           ['partner_id', 'cyc_notify_date'],
                                           order="cyc_notify_date asc")

        aml_partner = {}
        for aml in aml_notify_date:
            if aml['partner_id'][0] not in aml_partner:
                aml_partner.update({aml['partner_id'][0]: aml['cyc_notify_date']})

        for partner in all_partner:
            # Updating field worst cyc notify date
            if aml_partner.get(partner.id):
                partner.worst_cyc_notify_date = aml_partner.get(partner.id)
            else:
                partner.worst_cyc_notify_date = False

