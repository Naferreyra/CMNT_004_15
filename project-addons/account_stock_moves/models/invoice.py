from odoo import models, api, tools


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.model
    def invoice_line_move_line_get(self):
        res = super().invoice_line_move_line_get()
        if self.type == 'in_invoice':
            for line_data in res:
                i_line_id = line_data['invl_id']
                i_line = self.env['account.invoice.line'].browse(i_line_id)
                if i_line.move_line_ids and \
                    i_line.purchase_line_id and \
                        i_line.product_id.valuation == 'real_time':
                    purchase_line = i_line.purchase_line_id
                    qty = i_line.quantity
                    if i_line.product_id.cost_method in ['average', 'fifo'] \
                            and purchase_line.price_unit:
                        price_unit = purchase_line.price_unit * (1-(purchase_line.discount/100))
                        purchase_price = price_unit * qty
                    else:
                        price_unit = i_line.product_id.standard_price
                        purchase_price = price_unit * qty
                    line_data['price_purchase'] = purchase_price
                    line_data['purchase_line'] = purchase_line
                    move_lines = i_line.move_line_ids.filtered(
                        lambda x: x.picking_id and
                        x.picking_type_code == 'incoming' and
                        x.state not in ('draft', 'cancel'))
                    if len(move_lines) > 1:
                        line_data['create_date'] = \
                            i_line.move_line_ids[0]._get_origin_create_date()
                    else:
                        line_data['create_date'] = move_lines.create_date
            res.extend(self._cost_diff_move_lines(res))
        return res

    @api.model
    def _cost_diff_move_lines(self, res):
        diff_res = []
        # calculate and write down the possible price difference
        # between invoice price and product price
        for line in res:
            i_line_id = line['invl_id']
            i_line = self.env['account.invoice.line'].browse(i_line_id)
            fpos = i_line.invoice_id.fiscal_position_id
            # get the price difference account at the product
            acc = i_line.product_id.property_account_creditor_price_difference
            if not acc:
                # if not found on the product get the price difference
                # account at the category
                acc = i_line.product_id.categ_id.\
                    property_account_creditor_price_difference_categ
            acc = fpos.map_account(acc).id
            a = i_line.product_id.product_tmpl_id.\
                get_product_accounts(fiscal_pos=fpos)['stock_input'].id
            if 'purchase_line' in line \
                    and line['purchase_line'].currency_id.id != i_line.invoice_id.currency_id.id:
                line['price_purchase'] = line['purchase_line'].currency_id. \
                    with_context(date=line['create_date']). \
                    compute(line['price_purchase'], i_line.invoice_id.currency_id, round=True)
            price_subtotal = i_line.price_subtotal
            if 'price_purchase' in line and acc and \
                    tools.float_compare(line['price_purchase'], price_subtotal, 2):
                price_diff = price_subtotal - line['price_purchase']
                if tools.float_is_zero(price_diff, 2):
                    continue

                diff_res.append({
                    'type': 'src',
                    'name': i_line.name.split('\n')[0][:64],
                    'price_unit': price_diff,
                    'quantity': line['quantity'],
                    'price': price_diff,
                    'account_id': acc,
                    'product_id': line['product_id'],
                    'uom_id': line['uom_id'],
                    'account_analytic_id': line['account_analytic_id']
                    })
                diff_res.append({
                    'type': 'src',
                    'name': i_line.name.split('\n')[0][:64],
                    'price_unit': -price_diff,
                    'quantity': line['quantity'],
                    'price': -price_diff,
                    'account_id': a,
                    'product_id': line['product_id'],
                    'uom_id': line['uom_id'],
                    'account_analytic_id': line['account_analytic_id']
                    })
        return diff_res
