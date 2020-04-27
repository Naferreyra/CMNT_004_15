# Copyright 2019 Omar Castiñeira, Comunitea Servicios Tecnológicos S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api, _, fields, tools
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError


class StockLandedCost(models.Model):

    _inherit = 'stock.landed.cost'
    _order = 'write_date desc'

    account_journal_id = fields.\
        Many2one(default=lambda self: self.env['account.journal'].
                 search([('code', '=', 'APUR')]))

    container_ids = fields.Many2many('stock.container', string='Containers',
                                     compute='_get_container', inverse='_set_pickings',
                                     search='_search_container')
    forwarder_invoice = fields.Char(string='Forwarder Invoice', required=True)

    @api.multi
    def _get_container(self):
        move_obj = self.env['stock.move']
        for cost in self:
            res = []
            for picking_id in cost.picking_ids:
                move_id = move_obj.search([('picking_id', '=', picking_id.id),
                                           ('container_id', '!=', False)],
                                          limit=1)
                res.append(move_id.container_id.id)

            cost.container_ids = res

    @api.multi
    def _set_pickings(self):
        for cost in self:
            if not cost.picking_ids:
                res = []
                for container in cost.container_ids:
                    for picking in container.picking_ids:
                        res.append(picking.id)
                cost.picking_ids = res

    @api.model
    def _search_container(self, operator, value):
        moves = self.env['stock.move'].search([('container_id.name', operator, value)])
        pickings = moves.mapped('picking_id.id')
        return[('picking_ids', 'in', pickings)]

    @api.multi
    def check_lines_hscode(self, vals):
        product = self.env['product.product'].browse(vals.get('product_id'))
        if product and not product.hs_code_id:
            raise UserError(_('Not all the products have HS Code: %s') % product.default_code)

    @api.multi
    def compute_landed_cost(self):
        AdjustementLines = self.env['stock.valuation.adjustment.lines']
        AdjustementLines.search([('cost_id', 'in', self.ids)]).unlink()

        digits = dp.get_precision('Product Price')(self._cr)
        towrite_dict = {}
        for cost in self.filtered(lambda cost: cost.picking_ids):
            total_qty = 0.0
            total_cost = 0.0
            total_weight = 0.0
            total_volume = 0.0
            total_line = 0.0
            total_tariff = 0.0
            currency_change = 0.0

            all_val_line_values = cost.get_valuation_lines()
            for val_line_values in all_val_line_values:
                self.check_lines_hscode(val_line_values)
                for cost_line in cost.cost_lines:
                    val_line_values.update({'cost_id': cost.id,
                                            'cost_line_id': cost_line.id})
                    self.env['stock.valuation.adjustment.lines'].\
                        create(val_line_values)
                total_qty += val_line_values.get('quantity', 0.0)
                total_weight += val_line_values.get('weight', 0.0)
                total_volume += val_line_values.get('volume', 0.0)
                total_tariff += val_line_values.get('tariff', 0.0)
                former_cost = val_line_values.get('former_cost', 0.0)
                total_cost += tools.float_round(former_cost,
                                                precision_digits=digits[1]) \
                    if digits else former_cost

                total_line += 1

            for line in cost.cost_lines:
                value_split = 0.0
                if line.split_method == 'by_tariff':
                    currency_change = line.price_unit / total_tariff
                for valuation in cost.valuation_adjustment_lines:
                    value = 0.0
                    if valuation.cost_line_id and valuation.\
                            cost_line_id.id == line.id:
                        if line.split_method == 'by_quantity' and total_qty:
                            per_unit = (line.price_unit / total_qty)
                            value = valuation.quantity * per_unit
                        elif line.split_method == 'by_weight' and total_weight:
                            per_unit = (line.price_unit / total_weight)
                            value = valuation.weight * per_unit
                        elif line.split_method == 'by_volume' and total_volume:
                            per_unit = (line.price_unit / total_volume)
                            value = valuation.volume * per_unit
                        elif line.split_method == 'equal':
                            value = (line.price_unit / total_line)
                        elif line.split_method == 'by_current_cost_price' and total_cost:
                            per_unit = (line.price_unit / total_cost)
                            value = valuation.former_cost * per_unit
                        elif line.split_method == 'by_tariff' and total_tariff:
                            # per_unit = (line.price_unit / total_tariff)
                            value = valuation.tariff * currency_change
                        else:
                            value = (line.price_unit / total_line)

                        if digits:
                            value = tools.\
                                float_round(value, precision_digits=digits[1],
                                            rounding_method='UP')
                            fnc = min if line.price_unit > 0 else max
                            value = fnc(value, line.price_unit - value_split)
                            value_split += value

                        if valuation.id not in towrite_dict:
                            towrite_dict[valuation.id] = value
                        else:
                            towrite_dict[valuation.id] += value
        for key, value in towrite_dict.items():
            AdjustementLines.browse(key).\
                write({'additional_landed_cost': value})
        return True

    def get_valuation_lines(self):
        lines = []

        for move in self.mapped('picking_ids').mapped('move_lines'):
            if move.product_id.valuation != 'real_time' or \
                    move.product_id.cost_method != 'fifo':
                continue
            vals = {
                'product_id': move.product_id.id,
                'move_id': move.id,
                'quantity': move.product_qty,
                'former_cost': move.value,
                'cost_purchase': (move.purchase_line_id.price_subtotal/move.purchase_line_id.product_qty) * move.product_qty,
                'weight': move.product_id.weight * move.product_qty,
                'volume': move.product_id.volume * move.product_qty,
                'tariff': round(move.purchase_line_id.price_subtotal *
                                (move.product_id.tariff/100), 4)
            }
            lines.append(vals)

        if not lines and self.mapped('picking_ids'):
            raise UserError(_('The selected picking does not contain any move '
                              'that would be impacted by landed costs. Landed '
                              'costs are only possible for products '
                              'configured in real time valuation with real '
                              'price costing method. Please make sure it is '
                              'the case, or you selected the correct picking'))
        return lines


class StockValuationAdjustmentLines(models.Model):

    _inherit = 'stock.valuation.adjustment.lines'

    @api.multi
    @api.depends('former_cost', 'quantity', 'additional_landed_cost', 'cost_purchase')
    def _get_new_move_cost(self):
        for line in self:
            line.new_unit_cost = (line.former_cost +
                                  line.additional_landed_cost) / \
                (line.quantity or 1.0)

    @api.multi
    @api.depends('cost_purchase', 'quantity')
    def _compute_cost_purchase_per_unit(self):
        for line in self:
            line.cost_purchase_per_unit = \
                line.cost_purchase / (line.quantity or 1.0)

    new_unit_cost = fields.Float('New standard price', store=True,
                                 compute="_get_new_move_cost")
    tariff = fields.Float("Tariff", digits=(16, 2))
    cost_purchase = fields.Float(
        'Purchase Price', digits=dp.get_precision('Product Price'))
    cost_purchase_per_unit = fields.Float(
        'Purchase Price (Per Unit)', compute='_compute_cost_purchase_per_unit',
        digits=0, store=True)


class StockLandedCostLines(models.Model):
    _inherit = 'stock.landed.cost.lines'

    split_method = fields.Selection(selection_add=[('by_tariff',
                                                    'By tariff')])

    @api.onchange('product_id')
    def onchange_product_id(self):
        super().onchange_product_id()
        if self.product_id:
            self.account_id = \
                self.product_id.property_stock_account_input.id or \
                self.product_id.categ_id.\
                property_stock_account_input_categ_id.id
