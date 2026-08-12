import unittest

from app.metadata.SeriesIndexer import NormalizeSeriesTitle, ParseSeriesTitle
from app.routers.VideosRouter import CalculateStringSimilarity
from app.schemas import Genre


ANIME_GENRES: list[Genre] = [Genre(major='アニメ・特撮', middle='国内アニメ')]


class SeriesIndexerTest(unittest.TestCase):
    """実際の EPG 表記を使って Series の確定的なタイトル解析を検証する。"""

    def test_cross_channel_title_variants_match(self) -> None:
        """放送枠名やアニメ表記が異なっても同じ作品キーになる。"""

        title_pairs = [
            (
                '<アニメギルド>最強出涸らし皇子の暗躍帝位争い #6',
                '最強出涸らし皇子の暗躍帝位争い #6',
            ),
            (
                '追放された転生重騎士はゲーム知識で無双する#06◆スーパーアニメイズムTURBO[字][デ]',
                '[字]アニメ 追放された転生重騎士はゲーム知識で無双する Chapter 6',
            ),
            (
                'バンドリ！ ゆめ∞みた #7「こころあらたに」[字]',
                'アニメ バンドリ！ ゆめ∞みた #07 こころあらたに',
            ),
        ]

        for first_title, second_title in title_pairs:
            with self.subTest(first_title=first_title):
                first = ParseSeriesTitle(first_title, ANIME_GENRES)
                second = ParseSeriesTitle(second_title, ANIME_GENRES)
                self.assertIsNotNone(first)
                self.assertIsNotNone(second)
                assert first is not None and second is not None
                self.assertEqual(first.normalized_title, second.normalized_title)

    def test_seasons_remain_separate(self) -> None:
        """ローマ数字や期数は削除せず、別シーズンを別作品として扱う。"""

        second_season = ParseSeriesTitle('無職転生Ⅱ ～異世界行ったら本気だす～ 第21話', ANIME_GENRES)
        third_season = ParseSeriesTitle('無職転生Ⅲ ～異世界行ったら本気だす～ #01', ANIME_GENRES)
        self.assertIsNotNone(second_season)
        self.assertIsNotNone(third_season)
        assert second_season is not None and third_season is not None
        self.assertNotEqual(second_season.normalized_title, third_season.normalized_title)

    def test_generic_programs_are_not_indexed(self) -> None:
        """放送状態や汎用ニュース枠は話数らしい数字があっても Series にしない。"""

        self.assertIsNone(ParseSeriesTitle('ニュース #1', ANIME_GENRES))
        self.assertIsNone(ParseSeriesTitle('[4K](放送休止)', ANIME_GENRES))
        self.assertIsNone(ParseSeriesTitle('weather report 1', ANIME_GENRES))

    def test_episode_notations_are_extracted_without_changing_the_work(self) -> None:
        """小数話・空白入り話数・漢数字・括弧話数を同じ作品へ寄せる。"""

        cases = [
            ('奇妙なアニメ #4.5「特別編」', '4.5', '特別編'),
            ('奇妙なアニメ 第 5 話 旅立ち', '5', '旅立ち'),
            ('奇妙なアニメ 第拾壱話「帰還」', '11', '帰還'),
            ('奇妙なアニメ 第百二十三話', '123', None),
            ('奇妙なアニメ 第〇七話', '7', None),
            ('奇妙なアニメ (第6話)', '6', None),
            ('奇妙なアニメ CH 07', '7', None),
            ('奇妙なアニメ #01・#02「一挙放送」', '1・2', '一挙放送'),
        ]

        expected_key = NormalizeSeriesTitle('奇妙なアニメ')
        for title, episode_number, subtitle in cases:
            with self.subTest(title=title):
                parsed = ParseSeriesTitle(title, ANIME_GENRES)
                self.assertIsNotNone(parsed)
                assert parsed is not None
                self.assertEqual(parsed.normalized_title, expected_key)
                self.assertEqual(parsed.episode_number, episode_number)
                self.assertEqual(parsed.subtitle, subtitle)

    def test_episode_like_number_in_work_title_is_preserved(self) -> None:
        """作品名側の期数や数字を話数として消さない。"""

        parsed = ParseSeriesTitle('16bitセンセーション ANOTHER LAYER #03', ANIME_GENRES)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.display_title, '16bitセンセーション ANOTHER LAYER')
        self.assertEqual(parsed.episode_number, '3')

    def test_program_without_explicit_episode_is_not_persisted(self) -> None:
        """同名の情報番組や映画を、放送時刻だけで長期 Series にしない。"""

        self.assertIsNone(ParseSeriesTitle('アニナビ☆イレブン！ 前編', ANIME_GENRES))
        self.assertIsNone(ParseSeriesTitle('劇場版 とても長い作品名', ANIME_GENRES))

    def test_old_character_set_false_positive_is_reduced(self) -> None:
        """同じ文字を多く含むだけで順序の異なるタイトルへ高得点を与えない。"""

        first = 'アイウエオカキクケコ'
        reordered = 'コケクキカオエウイア'
        self.assertLess(CalculateStringSimilarity(first, reordered), 0.7)

    def test_unicode_and_spacing_variants_match(self) -> None:
        """全角英数字・感嘆符・日本語間の空白差だけを吸収する。"""

        self.assertEqual(
            NormalizeSeriesTitle('ＬＶ９９９ の村人！'),
            NormalizeSeriesTitle('LV999の村人!'),
        )

    def test_lv999_quoted_episode_matches_bs_title(self) -> None:
        """作品名の LV999 は保持し、引用符内の Lv2 だけを話数として解釈する。"""

        mx = ParseSeriesTitle('LV999の村人 「Lv2 最高に馬鹿だから」[字]', ANIME_GENRES)
        bs = ParseSeriesTitle('<アニメギルド>LV999 の村人 #2', ANIME_GENRES)
        self.assertIsNotNone(mx)
        self.assertIsNotNone(bs)
        assert mx is not None and bs is not None
        self.assertEqual(mx.normalized_title, bs.normalized_title)
        self.assertEqual(mx.episode_number, '2')
        self.assertEqual(mx.subtitle, '最高に馬鹿だから')
        self.assertEqual(mx.display_title, 'LV999の村人')

    def test_lv_in_work_title_is_not_an_episode_without_quoted_prefix(self) -> None:
        """作品名本体に含まれる LV999 だけでは Series を自動生成しない。"""

        self.assertIsNone(ParseSeriesTitle('LV999の村人 総集編', ANIME_GENRES))


if __name__ == '__main__':
    unittest.main()
