# Type Hints を指定できるように
# ref: https://stackoverflow.com/a/33533514/17124142
from __future__ import annotations

from typing import TYPE_CHECKING

from tortoise import fields
from tortoise.models import Model as TortoiseModel


if TYPE_CHECKING:
    from app.models.RecordedProgram import RecordedProgram
    from app.models.User import User


class BangumiEpisodeCompletion(TortoiseModel):
    """Bangumi への視聴完了同期をユーザーとエピソード単位で保持する。"""

    # データベース上のテーブル名
    class Meta(TortoiseModel.Meta):
        table: str = 'bangumi_episode_completions'
        unique_together = (('user', 'bangumi_episode_id'),)

    id = fields.IntField(pk=True)
    # 同じ Bangumi エピソードの重播を複数録画しても、ユーザーごとに 1 回だけ同期する
    user: fields.ForeignKeyRelation[User] = \
        fields.ForeignKeyField('models.User', related_name=None, on_delete=fields.CASCADE)
    user_id: int
    bangumi_episode_id = fields.IntField()
    # どの録画で 90% を超えたかを追跡できるよう、同期元の録画を保持する
    source_recorded_program: fields.ForeignKeyNullableRelation[RecordedProgram] = \
        fields.ForeignKeyField('models.RecordedProgram', related_name=None, null=True, on_delete=fields.SET_NULL)
    source_recorded_program_id: int | None
    completed_at = fields.DatetimeField(auto_now_add=True)
