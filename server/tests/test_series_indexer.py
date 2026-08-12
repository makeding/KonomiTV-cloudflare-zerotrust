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

    def test_parenthesized_episode_does_not_split_the_series(self) -> None:
        """括弧付き話数の開き括弧を作品名に残さない。"""

        parenthesized = ParseSeriesTitle(
            'ここは俺に任せて先に行けと言ってから10年がたったら伝説になっていた。(第2話)',
            ANIME_GENRES,
        )
        ordinary = ParseSeriesTitle(
            'ここは俺に任せて先に行けと言ってから10年がたったら伝説になっていた。 第6話',
            ANIME_GENRES,
        )
        self.assertIsNotNone(parenthesized)
        self.assertIsNotNone(ordinary)
        assert parenthesized is not None and ordinary is not None
        self.assertEqual(parenthesized.normalized_title, ordinary.normalized_title)

    def test_real_broadcast_slot_variants_match(self) -> None:
        """引用符式と無括弧式の放送枠名だけを作品名から除外する。"""

        cases = [
            ('日5「ウィッチウォッチ」 #2[字][デ]', 'ウィッチウォッチ', '2'),
            ('アニメギルド落第賢者の学院無双#1[新]', '落第賢者の学院無双', '1'),
            ('アニメA・ポンコツ風紀委員とスカート丈が不適切なJKの話 #2', 'ポンコツ風紀委員とスカート丈が不適切なJKの話', '2'),
            ('火アニバル マリッジトキシン 第3話', 'マリッジトキシン', '3'),
        ]
        for title, expected_title, expected_episode in cases:
            with self.subTest(title=title):
                parsed = ParseSeriesTitle(title, ANIME_GENRES)
                self.assertIsNotNone(parsed)
                assert parsed is not None
                self.assertEqual(parsed.display_title, expected_title)
                self.assertEqual(parsed.episode_number, expected_episode)

    def test_historical_numerals_and_episode_units_are_supported(self) -> None:
        """EPG に現れる大字の漢数字と「講」「輪」を話数として読む。"""

        cases = [
            ('春夏秋冬代行者 春の舞 第弐話「名残雪」', '2'),
            ('春夏秋冬代行者 春の舞 第肆話「朝凪」', '4'),
            ('春夏秋冬代行者 春の舞 第拾参話「奪還」', '13'),
            ('3年Z組銀八先生 第10講[字]', '10'),
            ('アニメ リィンカーネーションの花弁 第十輪 顔の無い男', '10'),
        ]
        for title, expected_episode in cases:
            with self.subTest(title=title):
                parsed = ParseSeriesTitle(title, ANIME_GENRES)
                self.assertIsNotNone(parsed)
                assert parsed is not None
                self.assertEqual(parsed.episode_number, expected_episode)

    def test_episode_at_description_line_start_is_used_conservatively(self) -> None:
        """title が固定の放送局では description の独立行先頭から話数を読む。"""

        cases = [
            (
                '没落予定の貴族だけど、暇だったから魔法を極めてみた',
                '#2 リアム、冒険者になってみた\nあらすじ本文',
                '2',
                'リアム、冒険者になってみた',
            ),
            (
                '勇者のクズ[字]',
                'クズの「師匠」と自称「弟子」\n#17勇者の帰還',
                '17',
                '勇者の帰還',
            ),
            (
                'Aランクパーティを離脱した俺は、元教え子たちと迷宮深部を目指す。',
                '第2話 魔獣の棲む森',
                '2',
                '魔獣の棲む森',
            ),
        ]
        for title, description, expected_episode, expected_subtitle in cases:
            with self.subTest(title=title):
                parsed = ParseSeriesTitle(title, ANIME_GENRES, description)
                self.assertIsNotNone(parsed)
                assert parsed is not None
                self.assertEqual(parsed.episode_number, expected_episode)
                self.assertEqual(parsed.subtitle, expected_subtitle)

    def test_numbers_inside_description_body_are_not_used_as_episode(self) -> None:
        """あらすじ本文中の数字は Series 生成の根拠にしない。"""

        parsed = ParseSeriesTitle(
            '番組タイトル',
            ANIME_GENRES,
            '主人公は第2話の事件から10年後を思い出す。',
        )
        self.assertIsNone(parsed)

    def test_short_real_work_title_is_not_rejected_by_length(self) -> None:
        """短い実在作品名でも明示的な話数があれば Series 化する。"""

        parsed = ParseSeriesTitle('キルアオ[字]', ANIME_GENRES, '「ミツオカノレン」\n#12 殺し屋会議')
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.display_title, 'キルアオ')
        self.assertEqual(parsed.episode_number, '12')

    def test_quoted_work_title_after_program_type_is_preserved(self) -> None:
        """TVアニメや時代劇の種別後に引用された作品名を副題にしない。"""

        cases = [
            ('TVアニメ『乙女怪獣キャラメリゼ』第2話「開かない扉」[字]', '乙女怪獣キャラメリゼ', '開かない扉'),
            ('時代劇「長七郎江戸日記」 第10回「若後家には御用心」', '長七郎江戸日記', '若後家には御用心'),
        ]
        for title, expected_title, expected_subtitle in cases:
            with self.subTest(title=title):
                parsed = ParseSeriesTitle(title, ANIME_GENRES)
                self.assertIsNotNone(parsed)
                assert parsed is not None
                self.assertEqual(parsed.display_title, expected_title)
                self.assertEqual(parsed.subtitle, expected_subtitle)

    def test_generic_short_program_is_still_rejected(self) -> None:
        """短い作品名を許可しても、既知の汎用番組は Series 化しない。"""

        self.assertIsNone(ParseSeriesTitle('紅白なび(10)[字]', ANIME_GENRES))


if __name__ == '__main__':
    unittest.main()
