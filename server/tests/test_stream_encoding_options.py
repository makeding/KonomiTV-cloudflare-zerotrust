import unittest

from app.streams.StreamEncodingOptions import SplitLiveQualityAndEncodingOptions


class LiveStreamEncodingOptionsTest(unittest.TestCase):
    """ライブ配信専用画質が通常のエンコード画質へ混入しないことを検証する。"""

    def test_original_is_accepted_without_encoding_options(self) -> None:
        """原始 MPEG-TS 配信の original を専用画質として受け付ける。"""

        result = SplitLiveQualityAndEncodingOptions('original')

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.quality, 'original')
        self.assertEqual(result.encoding_options.buildSuffix(), '')

    def test_raw_mmts_remains_separate_from_original(self) -> None:
        """BS4K の Raw MMTS を original と混同せず専用画質のまま保持する。"""

        result = SplitLiveQualityAndEncodingOptions('raw-mmts')

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.quality, 'raw-mmts')
        self.assertEqual(result.encoding_options.buildSuffix(), '')

    def test_recorded_copy_quality_is_rejected_for_live_streams(self) -> None:
        """録画 HLS 専用の copy をライブ配信では受け付けない。"""

        self.assertIsNone(SplitLiveQualityAndEncodingOptions('copy'))


if __name__ == '__main__':
    unittest.main()
