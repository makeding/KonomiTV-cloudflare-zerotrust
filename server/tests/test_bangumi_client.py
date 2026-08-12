import unittest
from typing import Any

from app.utils.BangumiClient import BangumiClient


class BangumiClientTest(unittest.TestCase):
    """Bangumi 收藏候補の一括照合と視聴完了判定を検証する。"""

    def test_only_single_positive_integer_episode_is_accepted(self) -> None:
        """単一の正整数以外の話数は自動同期しない。"""

        self.assertEqual(BangumiClient.parseEpisodeNumber('12'), 12)
        self.assertIsNone(BangumiClient.parseEpisodeNumber('0'))
        self.assertIsNone(BangumiClient.parseEpisodeNumber('1・2'))
        self.assertIsNone(BangumiClient.parseEpisodeNumber('4.5'))
        self.assertIsNone(BangumiClient.parseEpisodeNumber(None))


    def test_long_title_matches_collection_subject_without_search(self) -> None:
        """長い EPG 作品名でも收藏一覧内の同名条目へ完全一致できる。"""

        expected_subject: dict[str, Any] = {
            'id': 590786,
            'type': 2,
            'name': 'ここは俺に任せて先に行けと言ってから10年がたったら伝説になっていた。',
            'name_cn': '『你们先走我断后』，于是10年后我成为了传说',
        }
        unrelated_subject: dict[str, Any] = {
            'id': 8365,
            'type': 2,
            'name': 'ここはグリーン・ウッド',
            'name_cn': '绿林寮',
        }

        matched_subject = BangumiClient._findSubject(
            'ここは俺に任せて先に行けと言ってから10年がたったら伝説になっていた。',
            [unrelated_subject, expected_subject],
        )

        self.assertIsNotNone(matched_subject)
        assert matched_subject is not None
        self.assertEqual(matched_subject['id'], 590786)


    def test_trailing_period_difference_is_ignored(self) -> None:
        """EPG だけが長い作品名の末尾句点を省略しても同じ收藏条目として扱う。"""

        subject = {
            'id': 590786,
            'type': 2,
            'name': 'ここは俺に任せて先に行けと言ってから10年がたったら伝説になっていた。',
            'name_cn': '',
        }
        matched_subject = BangumiClient._findSubject(
            'ここは俺に任せて先に行けと言ってから10年がたったら伝説になっていた',
            [subject],
        )

        self.assertIsNotNone(matched_subject)


    def test_ambiguous_collection_titles_are_not_matched(self) -> None:
        """同点の收藏条目が複数ある場合は誤って自動確定しない。"""

        subjects = [
            {'id': 1, 'type': 2, 'name': '同名作品', 'name_cn': ''},
            {'id': 2, 'type': 2, 'name': '同名作品', 'name_cn': ''},
        ]

        self.assertIsNone(BangumiClient._findSubject('同名作品', subjects))


    def test_playback_completion_is_decided_at_ninety_percent(self) -> None:
        """30 分番組は 27 分到達時点から完了と判定する。"""

        self.assertFalse(BangumiClient.isPlaybackCompleted(1619.9, 1800.0))
        self.assertTrue(BangumiClient.isPlaybackCompleted(1620.0, 1800.0))


if __name__ == '__main__':
    unittest.main()
