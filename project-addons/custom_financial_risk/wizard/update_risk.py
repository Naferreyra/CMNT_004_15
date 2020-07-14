from odoo import models, fields, _

class UpdatePartnerRisk(models.TransientModel):
    _name = 'update.partner.risk'

    partner_ids = fields.Many2many('res.partner', string="Partners to update risk",
                                   required=True,domain="[('customer','=',1), ('parent_id', '=', False),('supplier','=',0),('is_company','=',1)]" )
    new_risk = fields.Float(help="If this field is 0, the payment mode will be bank transfer and payment term will be prepaid")

    def action_update_risk(self):
        partners_without_team = []
        for partner in self.partner_ids:
            partner.insurance_credit_limit = self.new_risk
            if self.new_risk == 0:
                partner.company_credit_limit = self.new_risk
                if partner.team_id:
                    prepaid_id = partner.env['account.payment.term'].with_context(lang='en_US').search(
                        [('name', '=', 'Prepaid')])
                    partner.property_payment_term_id = prepaid_id.id
                    if partner.team_id.name == 'Portugal':
                        novobanco_id = partner.env['account.payment.mode'].search(
                            [('name', '=', 'Transferencia Novo Banco')])
                        partner.customer_payment_mode_id = novobanco_id.id
                    if partner.team_id.name in ('Italia', 'Norte Europa', 'DACH'):
                        caixa_id = partner.env['account.payment.mode'].search([('name', '=', 'Transferencia La Caixa')])
                        partner.customer_payment_mode_id = caixa_id.id
                    elif partner.team_id.name in ('Francia', 'Magreb'):
                        popular_id = partner.env['account.payment.mode'].search(
                            [('name', '=', 'Transferencia Popular')])
                        partner.customer_payment_mode_id = popular_id.id
                    elif partner.team_id.name == 'España':
                        sabadell_id = partner.env['account.payment.mode'].search(
                            [('name', '=', 'Transferencia Sabadell')])
                        partner.customer_payment_mode_id = sabadell_id.id
                else:
                    partners_without_team.append(partner.name)
        if partners_without_team:
            message = _(
                "It has not been possible to change the payment mode to transfer and the payment term to prepaid because they do not have a sales team: %s") % partners_without_team
            self.env.user.notify_warning(message=message, sticky=True)


