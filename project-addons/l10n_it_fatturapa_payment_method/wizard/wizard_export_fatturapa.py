from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.addons.l10n_it_fatturapa.bindings.fatturapa  import (

    FatturaElettronica,
    FatturaElettronicaHeaderType,
    DatiTrasmissioneType,
    IdFiscaleType,
    ContattiTrasmittenteType,
    CedentePrestatoreType,
    AnagraficaType,
    IndirizzoType,
    IscrizioneREAType,
    CessionarioCommittenteType,
    RappresentanteFiscaleType,
    DatiAnagraficiCedenteType,
    DatiAnagraficiCessionarioType,
    DatiAnagraficiRappresentanteType,
    TerzoIntermediarioSoggettoEmittenteType,
    DatiAnagraficiTerzoIntermediarioType,
    FatturaElettronicaBodyType,
    DatiGeneraliType,
    DettaglioLineeType,
    DatiBeniServiziType,
    DatiRiepilogoType,
    DatiGeneraliDocumentoType,
    DatiDocumentiCorrelatiType,
    ContattiType,
    DatiPagamentoType,
    DettaglioPagamentoType,
    AllegatiType,
    ScontoMaggiorazioneType,
    CodiceArticoloType
)
from odoo.tools.float_utils import float_round


class WizardExportFatturapa(models.TransientModel):
    _inherit = "wizard.export.fatturapa"

    # Override this function to get the fatturapa_pm_id from the payment_mode_id
    # and not from payment_term_id
    def setDatiPagamento(self, invoice, body):
        if invoice.payment_term_id:
            payment_line_ids = invoice.get_receivable_line_ids()
            if not payment_line_ids:
                return True
            DatiPagamento = DatiPagamentoType()
            if not invoice.payment_term_id.fatturapa_pt_id:
                raise UserError(
                    _('Payment term %s does not have a linked e-invoice '
                      'payment term.') % invoice.payment_term_id.name)
            # Custom: Check the new field instead of the payment_term
            if not invoice.payment_mode_id.fatturapa_pm_id:
                raise UserError(
                    _('Payment mode %s does not have a linked e-invoice '
                      'payment method.') % invoice.payment_mode_id.name)
            DatiPagamento.CondizioniPagamento = (
                invoice.payment_term_id.fatturapa_pt_id.code)
            move_line_pool = self.env['account.move.line']
            for move_line_id in payment_line_ids:
                move_line = move_line_pool.browse(move_line_id)
                ImportoPagamento = '%.2f' % float_round(
                    move_line.amount_currency or move_line.debit, 2)
                # Create with only mandatory fields
                DettaglioPagamento = DettaglioPagamentoType(
                    ModalitaPagamento=(
                        # Custom: Here is what we change instead the payment_term
                        invoice.payment_mode_id.fatturapa_pm_id.code),
                    ImportoPagamento=ImportoPagamento
                )

                # Add only the existing optional fields
                if move_line.date_maturity:
                    DettaglioPagamento.DataScadenzaPagamento = \
                        move_line.date_maturity
                partner_bank = invoice.partner_bank_id
                if partner_bank.bank_name:
                    DettaglioPagamento.IstitutoFinanziario = \
                        partner_bank.bank_name
                if partner_bank.acc_number and partner_bank.acc_type == 'iban':
                    DettaglioPagamento.IBAN = \
                        ''.join(partner_bank.acc_number.split())
                if partner_bank.bank_bic:
                    DettaglioPagamento.BIC = partner_bank.bank_bic
                DatiPagamento.DettaglioPagamento.append(DettaglioPagamento)
            body.DatiPagamento.append(DatiPagamento)
        return True
