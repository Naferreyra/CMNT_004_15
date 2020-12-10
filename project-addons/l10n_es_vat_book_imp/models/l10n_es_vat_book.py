from odoo import models


class L10nEsVatBook(models.Model):
    _inherit = 'l10n.es.vat.book'

    def _get_account_move_lines(self, taxes):
        sql = (
            """ SELECT
                    DISTINCT aml.id, aml.date
                FROM
                    account_move_line aml
                LEFT JOIN
                    account_move_line_account_tax_rel amlatr ON amlatr.account_move_line_id = aml.id
                WHERE
                    ((aml.date >= '%s') and (aml.date <= '%s'))
                    and ((amlatr.account_tax_id in %s) or (aml.tax_line_id in %s))
                    and aml.company_id = %s
                ORDER BY
                    aml.date desc,
                    aml.id desc
        """) % (self.date_start, self.date_end, tuple(taxes.ids), tuple(taxes.ids), self.env.user.company_id.id)
        self.env.cr.execute(sql)
        lines = self.env.cr.fetchall()
        lines = self.env['account.move.line'].browse([x[0] for x in lines])
        return lines
