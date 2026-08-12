from tortoise import fields
from tortoise.models import Model as TortoiseModel


class DeviceAuth(TortoiseModel):
    class Meta(TortoiseModel.Meta):
        table = 'device_auth'

    id = fields.IntField(pk=True)
    device_code_hash = fields.CharField(max_length=64, unique=True)
    user_code = fields.CharField(max_length=8, unique=True)
    device_name = fields.TextField()
    user = fields.ForeignKeyField('models.User', related_name=None, null=True, on_delete=fields.CASCADE)
    expires_at = fields.DatetimeField()
    created_at = fields.DatetimeField(auto_now_add=True)
