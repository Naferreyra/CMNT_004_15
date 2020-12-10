from odoo.addons.component.core import Component


class PaymentLineExporter(Component):
    _name = 'payment.line.exporter'
    _inherit = ['base.exporter']
    _apply_on = ['account.payment.line']
    _usage = 'record.exporter'

    def update(self, binding, mode):
        invoice = self.env['account.invoice'].search([('number', '=', binding.communication)])
        vals = {
            "odoo_id": binding.id,
            "code": binding.order_id.name,
            "date": binding.date,
            "invoice_id": invoice.id,
            "partner_id": binding.partner_id.id,
            "amount": binding.amount_currency,
        }
        if mode == "insert":
            return self.backend_adapter.insert(vals)
        else:
            return self.backend_adapter.update(binding.id, vals)

    def delete(self, binding):
        return self.backend_adapter.remove(binding.id)


class PaymentLineAdapter(Component):

    _name = 'account.payment.line.general.adapter'
    _inherit = 'middleware.adapter'
    _apply_on = 'account.payment.line'
    _middleware_model = 'paymentline'
