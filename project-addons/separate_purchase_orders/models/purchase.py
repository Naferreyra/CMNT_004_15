from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    state = fields.Selection(selection_add=[("purchase_order", "Purchase Order State")])

    parent_id = fields.Many2one('purchase.order',"Parent")


    def complete_purchase(self):
        completed_purchase = True
        for line in self.order_line:
            if line.product_qty != line.qty_invoiced_custom:
                completed_purchase = False
        if completed_purchase!=self.completed_purchase:
            self.write({'completed_purchase':completed_purchase})

    completed_purchase = fields.Boolean("Purchase completed")

    def _compute_picking_invoice_custom(self):
        purchase_orders = self.env['purchase.order'].search([("parent_id", '=', self.id)])
        if purchase_orders:
            self.picking_count_custom = len(purchase_orders.mapped('picking_ids'))
            self.invoice_count_custom = len(purchase_orders.mapped('invoice_ids'))
            self.purchase_count_custom = len(purchase_orders)

    picking_count_custom = fields.Integer(compute='_compute_picking_invoice_custom', default=0)
    invoice_count_custom = fields.Integer(compute='_compute_picking_invoice_custom', default=0)
    purchase_count_custom = fields.Integer(compute='_compute_picking_invoice_custom', default=0)


    def action_view_picking_custom(self):
        action = self.env.ref('stock.action_picking_tree_all')
        result = action.read()[0]
        result['context'] = {}
        pick_ids = self.env['purchase.order'].search([("parent_id", '=', self.id)]).mapped('picking_ids')
        if not pick_ids or len(pick_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % (pick_ids.ids)
        elif len(pick_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = pick_ids.id
        return result


    def action_view_invoice_custom(self):
        res = self.action_view_invoice()
        purchase_invoices = self.env['purchase.order'].search([("parent_id", '=', self.id)]).mapped('invoice_ids')
        if self.state == 'purchase_order' and purchase_invoices:
            if not purchase_invoices or len(purchase_invoices) > 1:
                res['domain'] = "[('id','in',%s)]" % purchase_invoices.ids
            elif len(purchase_invoices) == 1:
                result = self.env.ref('account.invoice_supplier_form', False)
                res['views'] = [(result and result.id or False, 'form')]
                res['res_id'] = purchase_invoices.id
        return res


    def action_view_purchase_orders_custom(self):
        purchase_orders = self.env['purchase.order'].search([("parent_id", '=', self.id)])
        action = self.env.ref('purchase.purchase_rfq').read()[0]
        if len(purchase_orders) > 0:
            action['domain'] = [('id', 'in', purchase_orders.ids)]
            action['context'] = [('id', 'in', purchase_orders.ids)]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action


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
                if move_without_picking_ids:
                    purchase_line.split_qty = sum(move_without_picking_ids.mapped("product_uom_qty"))
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
                                                                              False) > line.product_qty + line.production_qty:
                raise UserError(_("You cannot modify the product quantity over the production_qty"))

        return super(PurchaseOrderLine, self).write(vals)

    @api.multi
    def unlink(self):
        for line in self:
            if line.order_id.state == 'purchase_order' and line.production_qty != line.product_qty:
                raise UserError(_("You cannot delete a line that has confirmed quantities"))
        return super(PurchaseOrderLine, self).unlink()