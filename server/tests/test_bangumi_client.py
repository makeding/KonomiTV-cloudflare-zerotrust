import unittest
from datetime import datetime
from types import SimpleNamespace
from typing import Any, cast

from app.models.RecordedProgram import RecordedProgram
from app.utils.BangumiClient import BangumiClient


def CreateRecordedProgram(
    episode_number: str,
    start_time: datetime,
    subtitle: str | None = None,
) -> RecordedProgram:
    """
    Bangumi 候補の照合に必要な録画番組情報を作成する。

    Args:
        episode_number (str): EPG から抽出した話数。
        start_time (datetime): 録画番組の放送開始時刻。
        subtitle (str | None): EPG から抽出した各話副題。

    Returns:
        RecordedProgram: 照合テスト用の録画番組。
    """

    return cast(RecordedProgram, SimpleNamespace(
        series_title = '無職転生Ⅱ ～異世界行ったら本気だす～',
        episode_number = episode_number,
        subtitle = subtitle,
        start_time = start_time,
    ))


class BangumiClientTest(unittest.TestCase):
    """Bangumi の分割クールと各話を誤同期しない照合条件を検証する。"""

    def test_only_single_positive_integer_episode_is_accepted(self) -> None:
        """単一の正整数以外の話数は自動同期しない。"""

        self.assertEqual(BangumiClient.parseEpisodeNumber('12'), 12)
        self.assertIsNone(BangumiClient.parseEpisodeNumber('0'))
        self.assertIsNone(BangumiClient.parseEpisodeNumber('1・2'))
        self.assertIsNone(BangumiClient.parseEpisodeNumber('4.5'))
        self.assertIsNone(BangumiClient.parseEpisodeNumber(None))

    def test_continuous_sort_number_selects_second_cour_episode(self) -> None:
        """ep が 1 に戻っても sort が続く分割クールは通し話数で照合できる。"""

        recorded_program = CreateRecordedProgram('14', datetime(2024, 4, 7, 23, 0))
        episodes: list[dict[str, Any]] = [{
            'id': 1233194,
            'type': 0,
            'ep': 1,
            'sort': 13,
            'airdate': '2024-04-07',
            'name': '夢のマイホーム',
            'name_cn': '我梦想中的家',
        }]
        match = BangumiClient.scoreCandidate(
            recorded_program,
            [recorded_program],
            {'id': 444557, 'name': '無職転生Ⅱ ～異世界行ったら本気だす～', 'name_cn': ''},
            episodes,
        )

        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match.subject_id, 444557)
        self.assertEqual(match.episode_id, 1233194)
        self.assertGreaterEqual(match.score, BangumiClient.MINIMUM_MATCH_SCORE)

    def test_title_variant_needs_date_subtitle_and_sequence_evidence(self) -> None:
        """タイトル表記が異なる候補は、放送日・各話名・話数列が揃った場合だけ閾値を超える。"""

        recorded_program = CreateRecordedProgram('7', datetime(2026, 8, 13, 23, 0), 'こころあらたに')
        recorded_program.series_title = 'バンドリ！ ゆめ∞みた'
        episodes: list[dict[str, Any]] = [{
            'id': 7007,
            'type': 0,
            'ep': 7,
            'sort': 6,
            'airdate': '2026-08-13',
            'name': 'こころあらたに',
            'name_cn': '',
        }]
        match = BangumiClient.scoreCandidate(
            recorded_program,
            [recorded_program],
            {'id': 583729, 'name': 'BanG Dream! ゆめ∞みた', 'name_cn': ''},
            episodes,
        )

        self.assertIsNotNone(match)
        assert match is not None
        self.assertGreaterEqual(match.score, BangumiClient.MINIMUM_MATCH_SCORE)

        recorded_program.subtitle = None
        weak_match = BangumiClient.scoreCandidate(
            recorded_program,
            [recorded_program],
            {'id': 583729, 'name': 'BanG Dream! ゆめ∞みた', 'name_cn': ''},
            episodes,
        )
        self.assertIsNotNone(weak_match)
        assert weak_match is not None
        self.assertLess(weak_match.score, BangumiClient.MINIMUM_MATCH_SCORE)


if __name__ == '__main__':
    unittest.main()
