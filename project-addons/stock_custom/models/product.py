# © 2016 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# import seaborn as sns
# import pandas as pd
# from matplotlib import pyplot as plt
from odoo import api, fields, models, _, exceptions
from io import BytesIO
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import time
import base64
import matplotlib
matplotlib.use('Agg')


class ProductTemplate(models.Model):

    _inherit = 'product.template'
    date_start = fields.Date(
        "Start date",
        default=lambda *a: (datetime.now() - relativedelta(months=6)).strftime(
            '%Y-%m-%d'))
    date_end = fields.Date("End Date", default=fields.Date.today)
    period = fields.Selection([('week', 'Week'),
                               ('month', 'Month'),
                               ('year', 'Year')],
                              'Time Period', default='month')
    analysis_type = fields.Selection([('average', 'Average'),
                                      ('end_of_period', 'End of period')],
                                     'Type of analysis', default='average')
    stock_graphic = fields.Binary("Graph")
    name = fields.Char(translate=False)
    description_sale = fields.Text(translate=False)
    currency_purchase_id = fields.Many2one('res.currency', 'Currency',
                                           default=lambda self: self.env.user.company_id.currency_id.id)

    @api.model
    def create(self, vals):
        prod = super().create(vals)
        prod.property_valuation = prod.categ_id.property_valuation
        if self.env['ir.config_parameter'].sudo().get_param('country_code') == 'IT' \
                and not prod.seller_ids:
            supplierinfo = self.env['product.supplierinfo'].create({
                'name': 27,
                'min_qty': 1
            })
            prod.seller_ids = supplierinfo
        return prod

    def set_product_template_currency_purchase(self, currency):
        self.currency_purchase_id = currency


class ProductProduct(models.Model):

    _inherit = 'product.product'

    virtual_stock_cooked = fields.Float(
        'Stock Available Cooking', compute="_compute_virtual_stock_cooked")
    ref_visiotech = fields.Char('Visiotech reference')

    @api.model
    def _last_day_of_period(self, _date):
        if self.period == 'week':
            period_end = (
                date(_date.year, _date.month, _date.day) +
                relativedelta(weeks=1))
        elif self.period == 'year':
            period_end = (date(_date.year, 1, 1) + relativedelta(years=1))
        else:
            period_end = (
                date(_date.year, _date.month, 1) +
                relativedelta(months=1))
        return period_end + relativedelta(days=-1)

    def _get_periods(self):
        """
        :return: A list of tuples with the first and last date
        """
        periods = []
        end_date = fields.Date.from_string(self.date_end)
        start_date = fields.Date.from_string(self.date_start)

        date_aux = start_date
        while date_aux < end_date:
            end_period = self._last_day_of_period(date_aux)
            period = (date_aux, end_period)
            periods.append(period)
            date_aux = end_period + relativedelta(days=1)

        return periods

    def _get_stock_data(self):
        """
          :return: A list of tuples with the total of stock grouped
        """
        data = []
        # LOCATIONS = REAL + EXTERNAL STOCK
        locations = [self.env.ref("stock.stock_location_stock").id,
                     self.env.ref("location_moves.stock_location_external").id]

        for period in self._get_periods():
            start_period = period[0].strftime('%Y-%m-%d')
            end_period_aux = period[1]
            end_period = end_period_aux.strftime('%Y-%m-%d')
            end_period_seconds = time.mktime(end_period_aux.timetuple())
            total_stock = 0
            if self.analysis_type == 'average':
                for loc in locations:
                    stock_data = self.env['stock.inventory.line'].read_group(
                        [('product_id', '=', self.id),
                         ('create_date', '>=', start_period),
                         ('create_date', '<=', end_period),
                         ('inventory_id.name', 'like', 'VSTOCK Diario%'),
                         ('location_id', '=', loc)],
                        ['inventory_id', 'product_qty'],
                        ['inventory_id'])
                    total = 0
                    if stock_data:
                        for product_stock in stock_data:
                            total += product_stock['product_qty']
                        total /= len(stock_data)
                    total_stock += total

                if total_stock:
                    data.append([end_period_seconds, round(total_stock)])
            else:
                for loc in locations:
                    stock_data = self.env['stock.inventory.line'].read_group(
                        [('product_id', '=', self.id),
                         ('create_date', '>=', start_period),
                         ('create_date', '<=', end_period),
                         ('inventory_id.name', 'like', 'VSTOCK Diario%'),
                         ('location_id', '=', loc)],
                        ['inventory_id', 'product_qty'],
                        ['inventory_id'], limit=1, orderby='inventory_id DESC')
                    if stock_data:
                        total_stock += stock_data[0]['product_qty']

                if total_stock:
                    data.append([end_period_seconds, total_stock])
        return data

    def action_create_graph(self):
        for product in self:
            if not product.date_start and not product.date_end and not \
                        product.period and not product.analysis_type:
                now = datetime.now()
                product.date_start = (now - relativedelta(months=6)).strftime(
                    '%Y-%m-%d')
                product.date_end = now
                product.period = 'month'
                product.analysis_type = 'average'
            elif not product.date_start or not product.date_end or not \
                    product.period or not product.analysis_type:
                raise exceptions.UserError(_('You must set all filter values'))
            elif product.date_end < product.date_start:
                raise exceptions.UserError(
                    _('End date cannot be smaller than start date'))
            product.run_scheduler_graphic()

    # def run_scheduler_graphic(self):
    #     """
    #         Generate the graphs of stock and link it to the partner
    #     """
    #     self.ensure_one()
    #     period_filter = self.period
    #     if period_filter == 'week':
    #         format_xlabel = "%y-W%W"
    #     elif period_filter == 'year':
    #         format_xlabel = "%Y"
    #     else:
    #         format_xlabel = "%m-%y"
    #
    #     def int_to_date(x):
    #         return datetime(
    #             time.localtime(x).tm_year, time.localtime(x).tm_mon,
    #             time.localtime(x).tm_mday).strftime(format_xlabel)
    #
    #     data = self._get_stock_data()
    #     if data:
    #         # Get data
    #         df = pd.DataFrame()
    #         df['Date'] = list(range(len(data)))
    #         df['Stock'] = [x[1] for x in data]
    #
    #         min_stock = min(df['Stock'])
    #         max_stock = max(df['Stock'])
    #         if min_stock != max_stock:
    #             margin_y = (max_stock - min_stock) / 30
    #             offset_axis = (max_stock - min_stock) / 10
    #         else:
    #             margin_y = max_stock / 100
    #             offset_axis = max_stock / 10
    #         margin_x = 0
    #
    #         # Create plot with points
    #         sns.despine()
    #         sns.set_style("darkgrid", {"axes.labelcolor": "#363737",
    #                                    "ytick.color": "#59656d",
    #                                    "xtick.color": "#59656d"})
    #         sns_plot = sns.lmplot('Date', 'Stock', data=df, fit_reg=False,
    #                               height=5, aspect=1.7,
    #                               scatter_kws={"color": "#A61D34", "s": 30})
    #
    #         # Draw a line plot to join all points
    #         sns_plot.map(plt.plot, "Date", "Stock", marker="o",
    #                      ms=4, color='#A61D34')
    #         plt.xticks(list(range(len(data))),
    #                    [int_to_date(x[0]) for x in data])
    #         [sns_plot.ax.text(p[0] - margin_x, p[1] + margin_y,
    #                           '%d' % int(p[1]), color='grey',
    #                           fontsize=9, ha="center")
    #          for p in zip(sns_plot.ax.get_xticks(), df['Stock'])]
    #
    #         # Set axis config
    #         plt.ylim(min_stock - offset_axis, max_stock + offset_axis)
    #         sns_plot.set_xticklabels(rotation=30)
    #
    #         # Create the graphic with the data
    #         io = BytesIO()
    #         sns_plot.savefig(io, format='png')
    #         io.seek(0)
    #         img_data = base64.b64encode(io.getvalue())
    #         plt.close()
    #         self.write({'stock_graphic': img_data})
    #
    #     return

    def _compute_virtual_stock_cooked(self):
        for product in self:
            product.virtual_stock_cooked = product.qty_available_wo_wh +\
                                            product.virtual_stock_conservative

    def action_view_moves(self):
        return {
            'domain': "[('product_id','=', " + str(self.id) + ")]",
            'name': _('Stock moves'),
            'view_mode': 'tree,form',
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
            'view_mode': 'tree,form',
            'view_type': 'form',
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
        res= super().set_product_last_purchase(order_id)
        PurchaseOrderLine = self.env['purchase.order.line']
        if not self.check_access_rights('write', raise_exception=False):
            return
        for product in self:
            currency_purchase_id = product.env.user.company_id.currency_id.id
            if order_id:
                lines = PurchaseOrderLine.search([
                    ('order_id', '=', order_id),
                    ('product_id', '=', product.id)], limit=1)
            else:
                lines = PurchaseOrderLine.search(
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

    @api.onchange('type')
    def onchange_product_type(self):
        for product in self:
            if product.type=='service':
                product.invoice_policy = 'order'
            elif product.type=='product':
                product.invoice_policy = 'delivery'


class StockQuantityHistory(models.TransientModel):
    _inherit = 'stock.quantity.history'

    def open_table(self):
        res = super().open_table()
        if res.get('domain'):
            res['domain'] = "[('type', '=', 'product')]"
        return res
