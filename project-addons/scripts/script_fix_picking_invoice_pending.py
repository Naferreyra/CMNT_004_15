session.cr.execute("select distinct ail.invoice_id from account_invoice_line ail inner join stock_move sm on sm.invoice_line_id = ail.id where picking_id in (select sp.id from stock_picking sp inner join account_move am on am.id = sp.pending_invoice_move_id where sp.state = 'done' and sp.pending_invoice_move_id is not null and am.reversal_id is null and sp.id in (select distinct picking_id from stock_move sm where purchase_line_id is not null and sm.purchase_line_id in (select purchase_line_id from account_invoice_line ail inner join account_invoice ai on ai.id = ail.invoice_id where ai.state in ('open', 'paid'))))")
invoices = session.cr.fetchall()
invoices = [x[0] for x in invoices]
for invoice in invoices_obj:
    purchase_lines = invoice.invoice_line_ids.mapped('purchase_line_id')
    if purchase_lines:
        moves = session.env['stock.move'].search([('purchase_line_id', '=', purchase_lines.ids),('state', '=', 'done')])
        for picking in moves.mapped('picking_id'):
            if picking.pending_invoice_move_id and (picking.pending_invoice_move_id.to_be_reversed or not picking.pending_invoice_move_id.reversal_id):
                date = (invoice.date or invoice.date_invoice)
                picking.pending_invoice_move_id.create_reversals(date, reconcile=True)

session.cr.commit()


session.cr.execute("select id from stock_picking where pending_stock_move_id is not null and pending_stock_reverse_move_id is not null and exists (select 1 from stock_move sm inner join purchase_order_line pol on sm.purchase_line_id = pol.id where pol.currency_id != 1 and pol.currency_id is not null and sm.picking_id = stock_picking.id) and date_done >= '2019-07-01 00:00:00'")
pickings = session.cr.fetchall()
pickings = [x[0] for x in pickings]
for pick in session.env['stock.picking'].browse(pickings):
    date = pick.pending_stock_reverse_move_id.date
    pick.pending_stock_reverse_move_id.button_cancel()
    pick.pending_stock_reverse_move_id.unlink()
    pick.pending_stock_reverse_move_id = pick.pending_stock_move_id.create_reversals(date, reconcile=False)

session.cr.commit()
