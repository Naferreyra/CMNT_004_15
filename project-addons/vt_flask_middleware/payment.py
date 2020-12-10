from peewee import CharField, IntegerField, DecimalField
from database import SyncModel


class PaymentLine(SyncModel):

    odoo_id = IntegerField(unique=True)
    code = CharField(max_length=60)
    date = CharField(max_length=60)
    invoice_id = IntegerField()
    partner_id = IntegerField()
    amount = DecimalField(rounding='ROUND_HALF_EVEN')

    MOD_NAME = 'paymentline'

    def __unicode__(self):
        return "%s - %s" % (self.code, self.invoice_id)
