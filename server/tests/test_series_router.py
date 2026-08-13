import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from app.constants import JST
from app.routers.SeriesRouter import (
    ON_AIR_SERIES_GENRES,
    ExtractOfficialWebsiteURL,
    GetSeriesSummaries,
    OnAirSeriesListAPI,
    SeriesListPositionAPI,
)


class SeriesRouterTest(unittest.TestCase):
    """Series 一覧・詳細へ公開する外部リンクの抽出を検証する。"""

    def test_official_website_is_extracted_from_epg_detail(self) -> None:
        """公式欄の SNS より後ろにある作品公式サイトを選ぶ。"""

        self.assertEqual(
            ExtractOfficialWebsiteURL([
                '【公式X】https://x.com/example\n【公式サイト】https://example-anime.com/',
            ]),
            'https://example-anime.com/',
        )

    def test_streaming_and_social_links_are_not_official_website(self) -> None:
        """SNS と見逃し配信 URL だけの項目は公式サイトとして公開しない。"""

        self.assertIsNone(ExtractOfficialWebsiteURL([
            'https://tver.jp/series/example\nhttps://www.youtube.com/@example\nhttps://x.com/example',
        ]))

    def test_broadcaster_program_page_is_not_official_website(self) -> None:
        """放送局の番組ページは作品公式サイトとして公開しない。"""

        self.assertIsNone(ExtractOfficialWebsiteURL([
            '番組ホームページ https://www.bs4.jp/magilumiere2/',
        ]))

    def test_on_air_genres_are_limited_to_episode_based_programs(self) -> None:
        """On Air には定期放送を追うアニメ・ドラマ・バラエティ・音楽だけを掲載する。"""

        self.assertEqual(ON_AIR_SERIES_GENRES, {'アニメ・特撮', 'ドラマ', 'バラエティ', '音楽'})
        self.assertNotIn('ドキュメンタリー・教養', ON_AIR_SERIES_GENRES)


class SeriesRouterAsyncTest(unittest.IsolatedAsyncioTestCase):
    """Series の深いリンクを現在の一覧位置へ解決する処理を検証する。"""

    async def test_series_list_position_uses_current_search_and_descending_order(self) -> None:
        """検索中の 51 件目は、同じ降順条件の 2 ページ目として返す。"""

        connection = AsyncMock()
        connection.execute_query.return_value = (1, [{'row_number': 51}])
        with patch('app.routers.SeriesRouter.connections.get', return_value=connection):
            result = await SeriesListPositionAPI(123, query='作品', order='desc')

        self.assertEqual(result.page, 2)
        sql = connection.execute_query.await_args.args[0]
        self.assertIn('ORDER BY MAX(rv.file_created_at) DESC, s.id DESC', sql)
        self.assertIn('LOWER(s.title) LIKE LOWER(?)', sql)
        self.assertEqual(connection.execute_query.await_args.args[1], ['%作品%', '%作品%', 123])

    async def test_series_list_position_uses_ascending_order(self) -> None:
        """古い順の深いリンクでも一覧と同じ昇順を用いる。"""

        connection = AsyncMock()
        connection.execute_query.return_value = (1, [{'row_number': 1}])
        with patch('app.routers.SeriesRouter.connections.get', return_value=connection):
            result = await SeriesListPositionAPI(456, order='asc')

        self.assertEqual(result.page, 1)
        sql = connection.execute_query.await_args.args[0]
        self.assertIn('ORDER BY MAX(rv.file_created_at) ASC, s.id ASC', sql)

    async def test_series_summary_uses_only_generated_thumbnails(self) -> None:
        """一覧の重ねサムネイル候補は、サムネイル情報が生成済みの録画だけに絞る。"""

        now = datetime.now(JST)
        row = {
            'id': 1,
            'title': '作品',
            'description': '説明',
            'genres': '[]',
            'bangumi_subject_id': None,
            'bangumi_subject_name': None,
            'bangumi_subject_name_cn': None,
            'bangumi_subject_summary': None,
            'bangumi_subject_image_url': None,
            'thumbnail_recorded_program_ids': '[102, 101]',
            'channel_ids': '[]',
            'official_website_sources': '[]',
            'recorded_programs_count': 3,
            'latest_video_file_created_at': now.isoformat(),
            'created_at': now.isoformat(),
            'updated_at': now.isoformat(),
        }
        connection = AsyncMock()
        connection.execute_query.side_effect = [(1, [row]), (1, [{'count': 1}])]
        with patch('app.routers.SeriesRouter.connections.get', return_value=connection):
            result = await GetSeriesSummaries()

        self.assertEqual(result.series_list[0].thumbnail_recorded_program_ids, [102, 101])
        sql = connection.execute_query.await_args_list[0].args[0]
        self.assertIn('rv_thumbnail.thumbnail_info IS NOT NULL', sql)
        # 録画件数はサムネイルの有無にかかわらず全件を数える。
        self.assertEqual(result.series_list[0].recorded_programs_count, 3)

    async def test_on_air_accepts_first_episode_with_next_epg_and_weekly_variety(self) -> None:
        """初回だけ録画済みのアニメと、履歴で週次と分かるバラエティを掲載する。"""

        now = datetime.now(JST)
        anime_genres = json.dumps([{'major': 'アニメ・特撮', 'middle': '国内アニメ'}], ensure_ascii=False)
        variety_genres = json.dumps([{'major': 'バラエティ', 'middle': 'その他'}], ensure_ascii=False)
        documentary_genres = json.dumps([{'major': 'ドキュメンタリー・教養', 'middle': '歴史・紀行'}], ensure_ascii=False)
        recorded_rows = [
            {
                'series_id': 1, 'series_title': '新番組', 'genres': anime_genres,
                'program_title': '新番組 #1', 'id': 101, 'channel_id': 'gr011',
                'start_time': (now - timedelta(days=1)).isoformat(), 'episode_number': '1',
                'is_partially_recorded': True, 'has_thumbnail': True,
            },
            {
                'series_id': 1, 'series_title': '新番組', 'genres': anime_genres,
                'program_title': '新番組 #1 [再]', 'id': 102, 'channel_id': 'gr011',
                'start_time': now.isoformat(), 'episode_number': '1',
                'is_partially_recorded': False, 'has_thumbnail': False,
            },
            {
                'series_id': 2, 'series_title': '8K紀行', 'genres': documentary_genres,
                'program_title': '8K紀行 第1回', 'id': 201, 'channel_id': 'bs811',
                'start_time': (now - timedelta(days=1)).isoformat(), 'episode_number': '1',
                'is_partially_recorded': False, 'has_thumbnail': False,
            },
            {
                'series_id': 3, 'series_title': '週刊バラエティ', 'genres': variety_genres,
                'program_title': '週刊バラエティ #2', 'id': 302, 'channel_id': 'gr041',
                'start_time': (now - timedelta(days=1)).isoformat(), 'episode_number': '2',
                'is_partially_recorded': True, 'has_thumbnail': False,
            },
            {
                'series_id': 3, 'series_title': '週刊バラエティ', 'genres': variety_genres,
                'program_title': '週刊バラエティ #2', 'id': 303, 'channel_id': 'gr051',
                'start_time': (now - timedelta(days=1)).isoformat(), 'episode_number': '2',
                'is_partially_recorded': False, 'has_thumbnail': True,
            },
            {
                'series_id': 3, 'series_title': '週刊バラエティ', 'genres': variety_genres,
                'program_title': '週刊バラエティ #1', 'id': 301, 'channel_id': 'gr041',
                'start_time': (now - timedelta(days=8)).isoformat(), 'episode_number': '1',
                'is_partially_recorded': False, 'has_thumbnail': True,
            },
        ]
        future_rows = [{
            'title': '新番組 #2', 'description': '', 'genres': anime_genres,
            'start_time': (now + timedelta(days=6)).isoformat(),
        }]
        connection = AsyncMock()
        connection.execute_query.side_effect = [(len(recorded_rows), recorded_rows), (1, future_rows)]
        with patch('app.routers.SeriesRouter.connections.get', return_value=connection):
            result = await OnAirSeriesListAPI()

        self.assertEqual({series.id for series in result.series_list}, {1, 3})
        anime = next(series for series in result.series_list if series.id == 1)
        next_broadcast = now + timedelta(days=6)
        self.assertEqual(anime.weekday, next_broadcast.weekday())
        self.assertEqual(anime.broadcast_time, f'{next_broadcast.hour:02d}:{(next_broadcast.minute // 5) * 5:02d}')
        # 完全録画の再放送があれば、同じ話数の部分録画は警告対象にしない。
        self.assertEqual(anime.partially_recorded_episodes_count, 0)
        self.assertEqual(anime.thumbnail_recorded_program_ids, [101])
        weekly_variety = next(series for series in result.series_list if series.id == 3)
        self.assertEqual(weekly_variety.partially_recorded_episodes_count, 0)
        self.assertEqual(weekly_variety.thumbnail_recorded_program_ids, [303, 301])


if __name__ == '__main__':
    unittest.main()
