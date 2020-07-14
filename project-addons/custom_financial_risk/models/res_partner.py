# © 2019 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    risk_circulating_include = fields.Boolean(
        string='Include Circulating amount')
    risk_circulating_limit = fields.Monetary(
        string='Limit In Circulating amount', help='Set 0 if it is not locked')
    risk_circulating = fields.Monetary(
        compute='_compute_risk_circulating',
        string='Total Circulating amount',
        help='Total amount of circulating accounts')
    risk_invoice_draft = fields.Monetary(store=False)
    risk_invoice_open = fields.Monetary(store=False)
    risk_invoice_unpaid = fields.Monetary(store=False)
    risk_account_amount = fields.Monetary(store=False)
    risk_account_amount_unpaid = fields.Monetary(store=False)
    risk_sale_order = fields.Monetary(store=False)

    @api.multi
    def _compute_risk_sale_order(self):
        customers = self.filtered('customer')
        partners = customers | customers.mapped('child_ids')
        moves = self.env['stock.move'].search(
            [('sale_line_id.state', '=', 'sale'), ('sale_line_id.order_partner_id', 'in', partners.ids),
             ('picking_id', '!=', False), ('state', 'not in', ('cancel', 'done'))])
        sale_lines = moves.mapped('sale_line_id')

        # Search if the are some lines with products to be invoiced that may or may not have stock_moves(like services)
        sale_lines = sale_lines | self.env['sale.order.line'].search(
            [('invoice_status', '=', 'to invoice'), ('order_partner_id', 'in', partners.ids)])
        for partner in customers:
            partner_ids = (partner | partner.child_ids).ids
            # Take in account max of ordered qty and delivered qty or min if price is less of zero
            partner.risk_sale_order = sum(
                (max(line.price_total, line.amt_to_invoice) if line.price_total > 0
                 else min(line.price_total, line.amt_to_invoice)) - line.amt_invoiced for line in sale_lines if
                line.order_partner_id.id in partner_ids)

    @api.model
    def _risk_field_list(self):
        res = super()._risk_field_list()
        res.append(
            ('risk_circulating', 'risk_circulating_limit',
             'risk_circulating_include'))
        return res

    def _compute_risk_circulating(self):
        for partner in self:
            move_amount_curr = self.env['account.move.line'].read_group(
                [('partner_id', 'child_of', partner.id),
                 ('account_id.circulating', '=', True),
                 ('currency_id', '!=', False),
                 ('reconciled', '=', False)],
                ['partner_id', 'amount_residual_currency'],
                groupby='partner_id')
            move_amount = self.env['account.move.line'].read_group(
                [('partner_id', 'child_of', partner.id),
                 ('account_id.circulating', '=', True),
                 ('currency_id', '=', False),
                 ('reconciled', '=', False)],
                ['partner_id', 'amount_residual'],
                groupby='partner_id')
            total_amount = 0
            if move_amount_curr:
                total_amount += move_amount_curr[0]['amount_residual_currency']
            if move_amount:
                total_amount += move_amount[0]['amount_residual']
            if move_amount or move_amount_curr:
                partner.risk_circulating = total_amount
            else:
                partner.risk_circulating = 0.0
