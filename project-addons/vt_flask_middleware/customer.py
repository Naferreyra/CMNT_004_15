"""
User model and helper functions.

It will try to automatically create the user table and admin user
if they don't exist.
"""

from peewee import CharField, IntegerField, FloatField, ForeignKeyField, BooleanField, DateTimeField
from commercial import Commercial
from app import app
from database import SyncModel


class CustomerTag(SyncModel):
    """
    User tag model.

    Note: follows the 'user model' protocol specified by flask_peewee.auth.Auth
    """

    odoo_id = IntegerField(unique=True)
    name = CharField(max_length=70)
    parent_id = IntegerField(null=True)

    MOD_NAME = 'customertag'

    def __unicode__(self):
        return self.name


class Customer(SyncModel):
    """
    User model.

    Note: follows the 'user model' protocol specified by flask_peewee.auth.Auth
    """
    fiscal_name = CharField(max_length=150)
    commercial_name = CharField(max_length=150, null=True)
    pricelist_name = CharField(max_length=150, null=True)
    ref = CharField(max_length=150, null=True)
    discount = FloatField(default=0.0)
    vat = CharField(max_length=25, null=True)
    street = CharField(max_length=250, null=True)
    city = CharField(max_length=150, null=True)
    zipcode = CharField(max_length=8, null=True)
    country = CharField(max_length=100, null=True)
    state = CharField(max_length=100, null=True)
    email = CharField(max_length=70, null=True)
    odoo_id = IntegerField(unique=True)
    lang = CharField(max_length=5, null=True)
    type = CharField(max_length=30, null=True)
    parent_id = IntegerField(null=True)
    commercial_id = ForeignKeyField(Commercial, on_delete='CASCADE', null=True)
    is_company = BooleanField(default=True)
    prospective = BooleanField(default=False)
    phone1 = CharField(max_length=40, null=True)
    phone2 = CharField(max_length=40, null=True)
    is_prepaid_payment_term = BooleanField(default=False)
    last_sale_date = DateTimeField(formats=['%Y-%m-%d %H:%M:%S'])

    MOD_NAME = 'customer'

    def __unicode__(self):
        return self.fiscal_name


class CustomerTagCustomerRel(SyncModel):

    odoo_id = IntegerField()
    customertag_id = ForeignKeyField(CustomerTag, on_delete='CASCADE')

    MOD_NAME = 'customertagcustomerrel'

    def __unicode__(self):
        return "Customer id: %s - Tag id: %s" % (self.odoo_id, self.customertag_id)

