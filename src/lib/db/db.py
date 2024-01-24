import datetime
from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.postgres.fields import ArrayField


class banks(Model):
    card_num = fields.CharField(max_length=1024, pk=True)
    ccv = fields.CharField(max_length=4)
    exp_month = fields.CharField(max_length=3)
    exp_year = fields.CharField(max_length=3)
    name = fields.CharField(max_length=100)
    guild_id = fields.BigIntField()
    user_id = fields.BigIntField()
    default= fields.BooleanField(default=False)
    token = fields.CharField(max_length=1024, null=True)

class guild_config(Model):
    id = fields.BigIntField(pk=True)
    admins = ArrayField(fields.BigIntField())
    staff_role = fields.BigIntField()
    log_channel = fields.BigIntField()
    cashapp_pic = fields.CharField(max_length=6666)

class categories(Model):
    cat_id = fields.IntField(pk=True)
    type = fields.CharField(max_length=1024)

class keyauth(Model):
    user_id = fields.BigIntField(pk=True)
    key = fields.CharField(max_length=1024)

class prices(Model):
    vbucks = fields.IntField(pk=True)
    cost = fields.IntField()
    guild_id = fields.BigIntField()

class orders(Model):
    email = fields.CharField(max_length=1024)
    password = fields.CharField(max_length=1024)
    code = fields.CharField(pk=True, max_length=1024)
    guild_id = fields.BigIntField()
    paid = fields.BooleanField(default=False)
    delivered = fields.BooleanField(default=False)
    vbucks = fields.CharField(max_length=1024, null=True)
    cost = fields.CharField(max_length=1024, null=True)

class addons(Model):
    user_id = fields.BigIntField(pk=True)