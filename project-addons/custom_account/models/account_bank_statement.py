from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountBankStatementLine(models.Model):

    _inherit = "account.bank.statement.line"

    old_statement_id = fields.Integer()
    ignored_reason = fields.Text("Reason")
    statement_id = fields.Many2one(required=False)

    @api.multi
    def action_launch_ignore(self):
        return {
            'name': _('Ignore Statement Line'),
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'ignore.statement.line.wzd',
            'src_model': 'account.bank.statement.line',
            'type': 'ir.actions.act_window',
            'id': 'ignore_statement_line_wdz_view',
            }

    @api.multi
    def action_ignore(self, reason):
        for line in self:
            bank_statement = line.statement_id
            line.old_statement_id = line.statement_id.id
            line.statement_id = False
            line.ignored_reason = reason
            bank_statement.balance_end_real -= line.amount

    @api.multi
    def action_unignore(self):
        for line in self:
            if line.old_statement_id:
                line.statement_id = line.old_statement_id
                line.old_statement_id = False
                line.statement_id.balance_end_real += line.amount
            else:
                raise UserError(_('There is no old statement to link'))
