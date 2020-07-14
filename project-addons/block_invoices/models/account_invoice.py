# © 2019 Comunitea
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields, _, exceptions, api


class AccountInvoice(models.Model):

    _inherit = 'account.invoice'

    blocked = fields.Boolean(related='partner_id.blocked_sales', copy=False)
    allow_confirm_blocked = fields.Boolean('Allow confirm')

    def invoice_validate(self):
        """
        Herencia de uno de los métodos de la actividad 'open' del workflow
        de facturas para controlar el bloqueo de ventas a clientes
        """
        for invoice in self:
            # Compruebo la empresa actual y su padre...
            for partner in invoice.partner_id.get_partners_to_check():
                # Comprobar ventas bloqueadas si es una factura de un proveedor que es cliente también
                if invoice.type == 'in_invoice' and partner.customer and \
                        partner.blocked_sales and not invoice.allow_confirm_blocked:
                    if not invoice.sale_order_ids or \
                            (invoice.sale_order_ids
                             and any(not order.allow_confirm_blocked for order in invoice.sale_order_ids)):
                        message = _('Customer blocked by lack of payment. Check the maturity dates of their account move lines.')
                        raise exceptions.Warning(message)
        return super().invoice_validate()

    @api.onchange('partner_id')
    def onchange_partner_id_check_blocked(self):
        warning = {}
        title = False
        message = False
        # Compruebo la empresa actual y su padre...
        for partner in self.partner_id.get_partners_to_check():
            if partner.blocked_sales:
                title = _("Warning for %s") % partner.name
                message = _('Customer blocked by lack of payment. Check the maturity dates of their account move lines.')
                warning = {
                    'title': title,
                    'message': message
                    }
            return {'warning': warning}

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        values = super()._prepare_refund(invoice, date_invoice, date, description, journal_id)
        values.update({'allow_confirm_blocked': self.allow_confirm_blocked})
        return values

    def action_invoice_open(self):
        return super(AccountInvoice, self.with_context({'bypass_risk':True})).action_invoice_open()
