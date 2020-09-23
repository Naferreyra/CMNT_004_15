from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    state = fields.Selection(selection_add=[("purchase_order", "Purchase Order State")])

    parent_id = fields.Many2one('purchase.order',"Parent")

    order_split_ids = fields.One2many("purchase.order", "parent_id", "Split orders")

    @api.depends('order_line.product_qty', 'order_split_ids.order_line.qty_invoiced')
    def _compute_completed_purchase(self):
        for order in self:
            order.completed_purchase = False
            if all(line.product_qty == line.qty_invoiced_custom for line in order.order_line):
                order.completed_purchase = True

    completed_purchase = fields.Boolean("Purchase completed", compute='_compute_completed_purchase', store=True)

    def _compute_picking_invoice_custom(self):
        if self.order_split_ids:
            self.picking_count_custom = len(self.order_split_ids.mapped('picking_ids'))
            self.invoice_count_custom = len(self.order_split_ids.mapped('invoice_ids'))
            self.purchase_count_custom = len(self.order_split_ids)

    picking_count_custom = fields.Integer(compute='_compute_picking_invoice_custom', default=0)
    invoice_count_custom = fields.Integer(compute='_compute_picking_invoice_custom', default=0)
    purchase_count_custom = fields.Integer(compute='_compute_picking_invoice_custom', default=0)


    def action_view_picking_custom(self):
        action = self.env.ref('stock.action_picking_tree_all')
        result = action.read()[0]
        result['context'] = {}
        pick_ids = self.order_split_ids.mapped('picking_ids')
        if not pick_ids or len(pick_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % pick_ids.ids
        elif len(pick_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = pick_ids.id
        return result


    def action_view_invoice_custom(self):
        res = self.action_view_invoice()
        purchase_invoices = self.order_split_ids.mapped('invoice_ids')
        if self.state == 'purchase_order' and purchase_invoices:
            if not purchase_invoices or len(purchase_invoices) > 1:
                res['domain'] = "[('id','in',%s)]" % purchase_invoices.ids
            elif len(purchase_invoices) == 1:
                result = self.env.ref('account.invoice_supplier_form', False)
                res['views'] = [(result and result.id or False, 'form')]
                res['res_id'] = purchase_invoices.id
        return res


    def action_view_purchase_orders_custom(self):
        action = self.env.ref('purchase.purchase_rfq').read()[0]
        if self.order_split_ids:
            action['domain'] = [('id', 'in', self.order_split_ids.ids)]
            action['context'] = [('id', 'in', self.order_split_ids.ids)]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    @api.model
    def create(self,vals):
        if self._context.get("default_state",False)=="purchase_order":
            vals["name"] = self.env['ir.sequence'].next_by_code('split.purchase.orders.name') or 'New'
        return super(PurchaseOrder, self).create(vals)

    @api.multi
    def button_cancel(self):
        for order in self:
            if order.state=="purchase_order" and order.order_split_ids.filtered(lambda o:o.state!='cancel'):
                raise UserError(_("You cannot cancel an order that has separate orders. Please cancel them earlier."))
        return super(PurchaseOrder, self).button_cancel()

    @api.multi
    def button_purchase_order(self):
        return self.write({'state': 'purchase_order'})


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    parent_id = fields.Many2one('purchase.order.line')

    @api.multi
    def _compute_quantities(self):
        for purchase_line in self:
            purchase_order_lines = purchase_line.env['purchase.order.line'].search(
                [("parent_id", '=', purchase_line.id), ('state', '!=', 'cancel')])
            if purchase_order_lines:
                move_assigned_ids = purchase_order_lines.mapped('move_ids').filtered(lambda m,
                                                                                            line=purchase_line: m.picking_id and m.picking_id.state == "assigned" and m.state!='cancel' and m.purchase_line_id.parent_id.id == line.id)
                if move_assigned_ids:
                    purchase_line.shipment_qty = sum(move_assigned_ids.mapped("product_uom_qty"))
                purchase_line.qty_received_custom = sum(purchase_order_lines.mapped('qty_received'))
                purchase_line.qty_invoiced_custom = sum(purchase_order_lines.mapped('qty_invoiced'))
                move_without_picking_ids = purchase_order_lines.mapped('move_ids').filtered(lambda m,
                                                                                                   line=purchase_line: not m.picking_id and m.purchase_line_id.parent_id.id == line.id and m.state!='cancel')
                purchase_line.split_qty = sum (purchase_order_lines.filtered(lambda l: l.state=='draft').mapped('product_qty'))
                if move_without_picking_ids:
                    purchase_line.split_qty += sum(move_without_picking_ids.mapped("product_uom_qty"))
            purchase_line.production_qty = purchase_line.product_qty - purchase_line.split_qty - purchase_line.shipment_qty - purchase_line.qty_received_custom


    production_qty = fields.Float("Production Quantity", compute=_compute_quantities)
    split_qty = fields.Float("Split Quantity", compute=_compute_quantities)
    shipment_qty = fields.Float("Shipment Quantity", compute=_compute_quantities)

    qty_received_custom = fields.Float("Received Quantity", compute=_compute_quantities)
    qty_invoiced_custom = fields.Float("Invoiced Quantity", compute=_compute_quantities)

    @api.multi
    def write(self, vals):
        for line in self:
            if line.order_id.state == 'purchase_order' and vals.get('product_qty', False) and vals.get(
                    'product_qty') < line.split_qty+line.qty_received_custom+line.shipment_qty:
                raise UserError(_("You cannot modify the product quantity below the confirmed product quantity"))
            elif line.order_id.state == 'purchase_order' and vals.get('product_id', False) and line.production_qty != line.product_qty :
                raise UserError(_("You cannot modify the product because there are confirmed quantities"))
            if line.parent_id and vals.get('product_qty', False) and vals.get('product_qty',
                                                                              False) > line.product_qty + line.parent_id.production_qty:
                raise UserError(_("You cannot modify the product quantity over the production_qty"))

        return super(PurchaseOrderLine, self).write(vals)

    @api.multi
    def unlink(self):
        for line in self:
            if line.order_id.state == 'purchase_order' and line.production_qty != line.product_qty:
                raise UserError(_("You cannot delete a line that has confirmed quantities"))
        return super(PurchaseOrderLine, self).unlink()