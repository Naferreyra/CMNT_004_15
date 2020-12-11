
from peewee import CharField, IntegerField, FloatField, ForeignKeyField, DateTimeField
from database import SyncModel
from customer import Customer,CustomerTag
from product import ProductBrand,ProductCategory,Product

class CustomerSalePointProgrammeRule(SyncModel):

    odoo_id = IntegerField(unique=True)
    name = CharField(max_length=255)
    product_brand_id = ForeignKeyField(ProductBrand, on_delete='CASCADE', null=True)
    product_category_id = ForeignKeyField(ProductCategory, on_delete='CASCADE', null=True)
    product_id = ForeignKeyField(Product, on_delete='CASCADE', null=True)
    customertag_id = ForeignKeyField(CustomerTag, on_delete='CASCADE', null=True)
    date_end =  DateTimeField(formats=['%Y-%m-%d %H:%M:%S'],null=True)
    operator = CharField(max_length=30)
    value = FloatField(default=0.0)
    points = FloatField(default=0.0)
    MOD_NAME = 'Customersalepointprogrammerule'

    def __unicode__(self):
        return self.name

class CustomerSalePointProgramme(SyncModel):


    odoo_id = IntegerField(unique=True)
    name = CharField(max_length=255)
    partner_id = ForeignKeyField(Customer, on_delete='CASCADE')
    point_rule_id = ForeignKeyField(CustomerSalePointProgrammeRule, on_delete='CASCADE')
    points = FloatField(default=0.0)

    MOD_NAME = 'Customersalepointprogramme'

    def __unicode__(self):
        return "Customer: %s - Rule: %s" % (self.partner_id, self.point_rule_id)






