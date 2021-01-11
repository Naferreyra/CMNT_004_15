from odoo import models, api, exceptions, _


class AccountVoucherWizard(models.TransientModel):

    _inherit = "account.voucher.wizard"

    @api.constrains('amount_advance')
    def check_amount(self):
        if self.amount_advance <= 0:
            raise exceptions.ValidationError(_("Amount of advance must be "
                                               "positive."))
