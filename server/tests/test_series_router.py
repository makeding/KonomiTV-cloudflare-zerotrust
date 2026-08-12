import unittest

from app.routers.SeriesRouter import ExtractOfficialWebsiteURL


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


if __name__ == '__main__':
    unittest.main()
