# © 2016 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models, _, exceptions


class ProductTemplate(models.Model):

    _inherit = 'product.template'

    name = fields.Char(translate=False)
    description_sale = fields.Text(translate=False)

    # this doesn't seem to work
    property_valuation = fields.Selection(default='real_time')

    currency_purchase_id = fields.Many2one('res.currency', 'Currency',
                                           default=lambda self: self.env.user.company_id.currency_id.id)

    @api.model
    def create(self, vals):
        prod = super().create(vals)
        prod.property_valuation = 'real_time'
        return prod

    def set_product_template_currency_purchase(self, currency):
        self.currency_purchase_id = currency


class ProductProduct(models.Model):

    _inherit = 'product.product'

    ref_visiotech = fields.Char('Visiotech reference')


    def action_view_moves(self):
        return {
            'domain': "[('product_id','=', " + str(self.id) + ")]",
            'name': _('Stock moves'),
            'view_mode': 'tree',
            'view_type': 'form',
            'context': {'tree_view_ref': 'stock.view_move_tree',
                        'search_default_groupby_dest_location_id': 1,
                        'search_default_ready': 1,
                        'search_default_future': 1},
            'res_model': 'stock.move',
            'type': 'ir.actions.act_window',
        }

    def action_view_moves_dates(self):
        return {
            'domain': "[('product_id','=', " + str(self.id) + ")]",
            'name': _('Stock moves dates'),
            'view_mode': 'tree',
            'view_type' : 'form',
            'context': {'tree_view_ref': 'stock_custom.view_move_dates_tree',
                        'search_default_future_dates': 1},
            'res_model': 'stock.move',
            'type': 'ir.actions.act_window',
        }

    def get_stock_new(self):
        category_id = self.env['product.category'].search(
            [('name', '=', 'NUEVOS')])
        products = self.env['product.product'].search(
            [('categ_id', '=', category_id.id)])
        ids_products = [x.id for x in products
                        if x.qty_available > 0]
        return {
            'domain': "[('id','in', " + str(ids_products) + ")]",
            'name': _('Stock New'),
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'product.product',
            'type': 'ir.actions.act_window',
        }

    @api.multi
    def _compute_date_first_incoming(self):
        for product in self:
            moves = self.env['stock.move'].search(
                [('product_id', '=', product.id), ('picking_id', '!=', False),
                 ('purchase_line_id', '!=', False),('state','=','done'),('date_done','!=',False)],order='date_done asc', limit=1)
            if moves:
                product.date_first_incoming = moves.date_done
                product.date_first_incoming_reliability = "1.received"
            else:
                moves = self.env['stock.move'].search(
                    [('product_id', '=', product.id), ('purchase_line_id', '!=', False), ('state','!=','cancel')]).sorted(
                    key=lambda m: m.date_expected and m.date_reliability)
                if moves:
                    reliability = moves[0].date_reliability[1::]
                    number_reliability = str(int(moves[0].date_reliability[0]) + 1)
                    product.date_first_incoming_reliability = number_reliability+reliability
                    product.date_first_incoming = moves[0].date_expected

    date_first_incoming = fields.Datetime(compute=_compute_date_first_incoming, store=True)

    date_first_incoming_reliability = fields.Selection([
        ('1.received', 'Received'),
        ('2.high', 'High'),
        ('3.medium', 'Medium'),
        ('4.low', 'Low'),
        ])

    currency_purchase_id = fields.Many2one('res.currency', 'Currency',
                                           default=lambda self: self.env.user.company_id.currency_id.id)

    last_purchase_price = fields.Monetary(currency_field="currency_purchase_id")

    @api.multi
    def set_product_last_purchase(self, order_id=False):
        res = super().set_product_last_purchase(order_id)
        purchaseOrderLine = self.env['purchase.order.line']
        if not self.check_access_rights('write', raise_exception=False):
            return
        for product in self:
            currency_purchase_id = product.env.user.company_id.currency_id.id
            if order_id:
                lines = purchaseOrderLine.search([
                    ('order_id', '=', order_id),
                    ('product_id', '=', product.id)], limit=1)
            else:
                lines = purchaseOrderLine.search(
                    [('product_id', '=', product.id),
                     ('state', 'in', ['purchase', 'done'])]).sorted(
                    key=lambda l: l.order_id.date_order, reverse=True)

            if lines:
                # Get most recent Purchase Order Line
                last_line = lines[:1]
                currency_purchase_id = last_line.order_id.currency_id.id
            product.currency_purchase_id = currency_purchase_id
            # Set related product template values
            product.product_tmpl_id.set_product_template_currency_purchase(currency_purchase_id)
        return res


class StockQuantityHistory(models.TransientModel):
    _inherit = 'stock.quantity.history'

    def open_table(self):
        res = super().open_table()
        if res.get('domain'):
            res['domain'] = "[('type', '=', 'product')]"
        return res
