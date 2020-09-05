from odoo import fields, models, api, _
from odoo.exceptions import UserError


class MergePurchaseOrder(models.TransientModel):
    _name = 'merge.sale.order'

    merge_type = \
        fields.Selection([
            ('new_cancel',
             'Create new order and cancel all selected sale orders'),
            ('new_delete',
             'Create new order and delete all selected sale orders'),
            ('merge_cancel',
             'Merge order on existing selected order and cancel others'),
            ('merge_delete',
             'Merge order on existing selected order and delete others')],
            default='new_cancel', string="Merge Type")
    sale_order_id = fields.Many2one('sale.order', 'Sale Order')

    @api.onchange('merge_type')
    def onchange_merge_type(self):
        res = {}
        for order in self:
            order.sale_order_id = False
            if order.merge_type in ['merge_cancel', 'merge_delete']:
                sale_orders = self.env['sale.order'].browse(
                    self._context.get('active_ids', []))
                res['domain'] = {
                    'sale_order_id':
                        [('id', 'in',
                          [sale.id for sale in sale_orders])]
                }
            return res

    @api.multi
    def action_done(self):
        sale_orders = self.env['sale.order'].browse(
            self._context.get('active_ids', []))
        if len(sale_orders) < 2:
            raise UserError(_('Please select at least two sale orders'))
        partner = sale_orders[0].partner_id.id
        partner_shipping_id = sale_orders[0].partner_shipping_id.id
        partner_invoice_id = sale_orders[0].partner_invoice_id.id
        prepaid_option = sale_orders[0].prepaid_option
        for order in sale_orders:
            if order.state not in ('draft', 'reserve'):
                raise UserError(_('Please select Sale orders which are in Quotation or Reserve state'))
            if order.partner_id.id != partner:
                raise UserError(_('Please select Sale orders whose Customers are the same'))
            if order.partner_shipping_id.id != partner_shipping_id :
                raise UserError(_('Please select Sale orders whose shipping addresses are the same'))
            if order.partner_invoice_id.id != partner_invoice_id :
                raise UserError(_('Please select Sale orders whose invoice addresses are the same'))
            if order.prepaid_option != prepaid_option:
                raise UserError(_('Please all selected orders must have the same prepaid option'))
        if self.merge_type in ('new_cancel', 'new_delete'):
            so = self.env['sale.order'].create({'partner_id': partner, 'state': sale_orders[0].state, 'prepaid_option': prepaid_option})
            so.onchange_partner_id()
            self.merge_orders(sale_orders, so)
        else:
            so = self.sale_order_id
            self.merge_orders(sale_orders, so, True)

        if so.prepaid_option:
            so.calculate_prepaid_discount()

        return {
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('sale.view_order_form').id,
            'res_model': 'sale.order',
            'res_id': so.id,
            'type': 'ir.actions.act_window',
        }

    def merge_orders(self, sale_orders, so, merge_mode=False):
        notes=""
        internal_notes=""
        sale_notes=""
        for order in sale_orders:
            notes += order.note + "\n" if order.note else ""
            internal_notes += order.internal_notes + "\n" if order.internal_notes else ""
            sale_notes += order.sale_notes + "\n" if order.sale_notes else ""
            if merge_mode and order == so:
                continue
            for line in order.order_line:
                existing_so_line = False
                if so.order_line:
                    for so_line in so.order_line:
                        if line.product_id == so_line.product_id and \
                                line.price_unit == so_line.price_unit:
                            existing_so_line = so_line
                            break
                if existing_so_line:
                    if existing_so_line.product_id.categ_id.with_context(lang='es_ES').name != 'Portes':
                        existing_so_line.product_uom_qty += \
                            line.product_uom_qty
                        taxes = existing_so_line.tax_id + line.tax_id
                        existing_so_line.tax_id = [(6, 0, taxes.ids)]
                        analytic_tags = existing_so_line.analytic_tag_ids + line.analytic_tag_ids
                        existing_so_line.analytic_tag_ids = [(6, 0, analytic_tags.ids)]
                        if existing_so_line.reservation_ids:
                            line.reservation_ids.release()
                            existing_so_line.reservation_ids[0].reserve()
                        elif line.reservation_ids:
                            line.reservation_ids.release()
                            existing_so_line.stock_reserve()
                else:
                    old_so = line.order_id
                    line.order_id = so.id
                    for move in line.move_ids:
                        move.origin = so.name
                        move.name = move.name.replace(old_so.name, so.name)
                    if self.merge_type in ('new_cancel', 'merge_cancel'):
                        line.copy(default={'order_id': old_so.id})
        sale_orders_name = sale_orders.mapped('name')
        for order in sale_orders:
            if order != so:
                order.sudo().action_cancel()
                if self.merge_type in ('new_delete', 'merge_delete'):
                    order.sudo().unlink()
        so.note = notes
        so.internal_notes = internal_notes
        so.sale_notes = sale_notes
        so.message_post(body=_('This order has been created by merging these orders: %s')%sale_orders_name)
