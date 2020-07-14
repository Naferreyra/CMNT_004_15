from odoo import api, models, fields, _
from odoo.tools.safe_eval import safe_eval
import json


class CrmClaim(models.Model):
    _inherit = 'crm.claim'

    location = fields.Char('Location')

    @api.multi
    def find_claim_by_number_using_barcode(self, barcode):
        barcode = barcode.replace("-", "/")
        barcode = barcode.replace("'", "-")

        next_is_location = False

        if barcode.startswith('RMA'):
            claim = self.search([('number', '=', barcode)], limit=1)
            if claim:
                if claim.stage_id.name != "Pendiente de recibir":
                    message = _("The {} is already received").format(claim.number)
                    self.env.user.notify_warning(message=message, sticky=True)
                    next_is_location = True  # TODO: quitar esto al final (O NO!? puede servir para reubicar)
                else:
                    claim.message_post(body="RMA scanned")
                    claim.stage_id = self.env["crm.claim.stage"].search([('name', '=', 'Recibido')])
                    claim.date_received = fields.Date.today()
                    message = _("{} received").format(claim.number)
                    self.env.user.notify_info(title="RMA scanned", message=message)
                    next_is_location = True
            else:
                message = _("The RMA {} doesn't exist").format(barcode)
                self.env.user.notify_warning(message=message, sticky=True)
        elif self.id > 0:  # This means that we scanned an rma before and now we are scanning the location
            self.location = barcode
            message = _("The RMA {} is located at {}").format(self.number, barcode)
            self.env.user.notify_info(message=message)

        action = self.env.ref('rma_scanner.crm_claim_rma_scanner')
        result = action.read()[0]

        if next_is_location:
            context = safe_eval(result['context'])
            context.update({
                'default_state': 'warning',
                'default_status': _('Scan the location of the %s') % claim.number,
                'default_res_id': claim.id,
            })
            result['context'] = json.dumps(context)

        return result
