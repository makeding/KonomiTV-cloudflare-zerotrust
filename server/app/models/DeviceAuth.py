from __future__ import annotations

from typing import TYPE_CHECKING

from tortoise import fields
from tortoise.models import Model as TortoiseModel


if TYPE_CHECKING:
    from app.models.User import User


class DeviceAuth(TortoiseModel):
    class Meta(TortoiseModel.Meta):
        table = 'device_auth'

    id = fields.IntField(pk=True)
    device_code_hash = fields.CharField(max_length=64, unique=True)
    user_code = fields.CharField(max_length=8, unique=True)
    device_name = fields.TextField()
    user: fields.ForeignKeyNullableRelation[User] = \
        fields.ForeignKeyField('models.User', related_name=None, null=True, on_delete=fields.CASCADE)
    user_id: int | None
    expires_at = fields.DatetimeField()
    created_at = fields.DatetimeField(auto_now_add=True)
