from peewee import CharField, FloatField, IntegerField, ForeignKeyField
from database import SyncModel


class Translation(SyncModel):
    MOD_NAME = 'translation'

    model = CharField(max_length=60)
    field = CharField(max_length=60)
    res_id = IntegerField()
    lang = CharField(max_length=8)
    source = CharField(max_length=255)
    value = CharField(max_length=255)
    odoo_id = IntegerField(unique=True)

    def __unicode__(self):
        return "%s - %s - %s" % (self.model, self.field, self.res_id)
