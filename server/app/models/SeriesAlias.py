# Type Hints を指定できるように
# ref: https://stackoverflow.com/a/33533514/17124142
from __future__ import annotations

from typing import TYPE_CHECKING

from tortoise import fields
from tortoise.models import Model as TortoiseModel


if TYPE_CHECKING:
    from app.models.Series import Series


class SeriesAlias(TortoiseModel):
    """Bangumi 条目の統合後も旧放送局表記を同じ Series へ解決する。"""

    # データベース上のテーブル名
    class Meta(TortoiseModel.Meta):
        table: str = 'series_aliases'

    # SeriesIndexer が生成する完全一致用キーを主キーとし、別の Series への二重登録を防ぐ。
    normalized_title = fields.CharField(512, pk=True)
    series: fields.ForeignKeyRelation[Series] = \
        fields.ForeignKeyField('models.Series', related_name='aliases', on_delete=fields.CASCADE)
    series_id: int
