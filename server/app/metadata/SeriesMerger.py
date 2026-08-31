from __future__ import annotations

from datetime import datetime
from typing import Any

from tortoise import transactions

from app.constants import JST
from app.models.Series import Series


class SeriesMerger:
    """Bangumi で同一作品と確定した Series とその放送期間を統合する。"""

    @classmethod
    async def mergeByBangumiSubject(
        cls,
        series_id: int,
        subject_id: int,
        subject_name: str | None,
        subject_name_cn: str | None,
        subject_summary: str | None,
        subject_image_url: str | None,
    ) -> Series:
        """
        指定した Series を同じ Bangumi 条目に紐付く最古の Series へ原子的に統合する。

        Args:
            series_id (int): 今回 Bangumi 条目と照合できた Series ID。
            subject_id (int): Bangumi 条目 ID。
            subject_name (str | None): Bangumi 条目の原題。
            subject_name_cn (str | None): Bangumi 条目の中文題。
            subject_summary (str | None): Bangumi 条目の概要。
            subject_image_url (str | None): Bangumi 条目の画像 URL。

        Returns:
            Series: 統合後に残った最も ID が小さい Series。

        Raises:
            ValueError: 指定された Series が存在しない場合。
        """

        async with transactions.in_transaction() as connection:
            # 今回の照合対象と、すでに同じ条目 ID を保持する Series を同時にロック範囲へ入れる。
            ## SQLite は書き込みを直列化するため、以下の読み取りから削除まで他の API が半端な関連を観測しない。
            _, candidate_rows = await connection.execute_query(
                'SELECT id, normalized_title, title '
                'FROM series '
                'WHERE id = ? OR bangumi_subject_id = ? '
                'ORDER BY id ASC',
                [series_id, subject_id],
            )
            if not any(int(row['id']) == series_id for row in candidate_rows):
                raise ValueError(f'Series {series_id} was not found.')

            canonical_row = candidate_rows[0]
            canonical_series_id = int(canonical_row['id'])
            canonical_series_title = str(canonical_row['title'])

            # ID が小さい最古の Series を残し、それ以外の表記・放送期間・録画を順番に移す。
            for source_row in candidate_rows[1:]:
                source_series_id = int(source_row['id'])

                # 削除する Series の主タイトルと既存 alias を残し、将来の録画スキャンが再分割しないようにする。
                await connection.execute_query(
                    'UPDATE series_aliases SET series_id = ? WHERE series_id = ?',
                    [canonical_series_id, source_series_id],
                )
                await connection.execute_query(
                    'INSERT INTO series_aliases (normalized_title, series_id) VALUES (?, ?) '
                    'ON CONFLICT(normalized_title) DO UPDATE SET series_id = excluded.series_id',
                    [str(source_row['normalized_title']), canonical_series_id],
                )

                # 同一チャンネルの放送期間が両 Series にある場合は、日付範囲を外側へ広げて一方へ寄せる。
                _, source_period_rows = await connection.execute_query(
                    'SELECT id, channel_id, start_date, end_date '
                    'FROM series_broadcast_periods WHERE series_id = ?',
                    [source_series_id],
                )
                for source_period_row in source_period_rows:
                    source_period_id = int(source_period_row['id'])
                    _, canonical_period_rows = await connection.execute_query(
                        'SELECT id, start_date, end_date '
                        'FROM series_broadcast_periods '
                        'WHERE series_id = ? AND channel_id = ?',
                        [canonical_series_id, str(source_period_row['channel_id'])],
                    )
                    if len(canonical_period_rows) == 0:
                        await connection.execute_query(
                            'UPDATE series_broadcast_periods SET series_id = ? WHERE id = ?',
                            [canonical_series_id, source_period_id],
                        )
                        continue

                    canonical_period_row = canonical_period_rows[0]
                    canonical_period_id = int(canonical_period_row['id'])
                    start_date = min(
                        str(canonical_period_row['start_date']),
                        str(source_period_row['start_date']),
                    )
                    end_date = max(
                        str(canonical_period_row['end_date']),
                        str(source_period_row['end_date']),
                    )
                    await connection.execute_query(
                        'UPDATE series_broadcast_periods SET start_date = ?, end_date = ? WHERE id = ?',
                        [start_date, end_date, canonical_period_id],
                    )
                    await connection.execute_query(
                        'UPDATE recorded_programs SET series_broadcast_period_id = ? '
                        'WHERE series_broadcast_period_id = ?',
                        [canonical_period_id, source_period_id],
                    )
                    await connection.execute_query(
                        'DELETE FROM series_broadcast_periods WHERE id = ?',
                        [source_period_id],
                    )

                # 放送期間を先に完全移行してから Series FK と表示タイトルを更新する。
                ## 録画単位の Bangumi subject / episode ID は同じ作品の永続 ID なのでそのまま保持する。
                await connection.execute_query(
                    'UPDATE recorded_programs SET series_id = ?, series_title = ? WHERE series_id = ?',
                    [canonical_series_id, canonical_series_title, source_series_id],
                )
                await connection.execute_query('DELETE FROM series WHERE id = ?', [source_series_id])

            # 重複行を削除した後にだけ一意制約対象の subject ID を更新する。
            ## この順番により、同期中も同じ subject ID を持つ Series は常に 1 件に保たれる。
            await connection.execute_query(
                'UPDATE series SET '
                'bangumi_subject_id = ?, bangumi_subject_name = ?, bangumi_subject_name_cn = ?, '
                'bangumi_subject_summary = ?, bangumi_subject_image_url = ?, updated_at = ? '
                'WHERE id = ?',
                [
                    subject_id,
                    subject_name,
                    subject_name_cn,
                    subject_summary,
                    subject_image_url,
                    datetime.now(tz=JST),
                    canonical_series_id,
                ],
            )

        return await Series.get(id=canonical_series_id)
