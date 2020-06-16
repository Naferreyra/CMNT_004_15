from odoo import models, fields, api


class IgnoreStatementLineWzd(models.TransientModel):

    _name = 'ignore.statement.line.wzd'

    reason = fields.Text(required=True)

    @api.multi
    def action_ignore(self):
        statement_lines = self.env['account.bank.statement.line'].browse(self.env.context['active_ids'])
        for line in statement_lines:
            line.action_ignore(self.reason)
