from odoo import models, fields


class AccountAccount(models.Model):
    _inherit = "account.account"

    code = fields.Char(index=False)


class CurrencyRate(models.Model):
    _inherit = "res.currency.rate"

    name = fields.Date(index=False)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    user_type_id = fields.Many2one(index=False)


class AccountMove(models.Model):
    _inherit = "account.move"

    date = fields.Date(index=False)


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    uom_id = fields.Many2one(index=False)


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    name = fields.Char(index=False)
    date_due = fields.Date(index=False)


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    sequence = fields.Integer(index=False)


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    date = fields.Date(index=False)
    account_id = fields.Many2one(index=False)
