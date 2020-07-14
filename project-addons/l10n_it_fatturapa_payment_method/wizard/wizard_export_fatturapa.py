from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.addons.l10n_it_fatturapa.bindings.fatturapa_v_1_2 import (
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
            # Check the new field instead of the payment_term
            if not invoice.payment_mode_id.fatturapa_pm_id:
                raise UserError(
                    _('Payment term %s does not have a linked e-invoice '
                      'payment method.') % invoice.payment_term_id.name)
            DatiPagamento.CondizioniPagamento = (
                invoice.payment_term_id.fatturapa_pt_id.code)
            move_line_pool = self.env['account.move.line']
            for move_line_id in payment_line_ids:
                move_line = move_line_pool.browse(move_line_id)
                ImportoPagamento = '%.2f' % (
                    move_line.amount_currency or move_line.debit)
                DettaglioPagamento = DettaglioPagamentoType(
                    ModalitaPagamento=(
                        # Here is what we change instead the payment_term
                        invoice.payment_mode_id.fatturapa_pm_id.code),
                    DataScadenzaPagamento=move_line.date_maturity,
                    ImportoPagamento=ImportoPagamento
                    )
                if invoice.partner_bank_id:
                    DettaglioPagamento.IstitutoFinanziario = (
                        invoice.partner_bank_id.bank_name)
                    if invoice.partner_bank_id.acc_number:
                        DettaglioPagamento.IBAN = (
                            ''.join(invoice.partner_bank_id.acc_number.split())
                            )
                    if invoice.partner_bank_id.bank_bic:
                        DettaglioPagamento.BIC = (
                            invoice.partner_bank_id.bank_bic)
                DatiPagamento.DettaglioPagamento.append(DettaglioPagamento)
            body.DatiPagamento.append(DatiPagamento)
        return True
