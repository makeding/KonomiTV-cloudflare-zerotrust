import unittest
from datetime import datetime, timedelta

from app.constants import JST
from app.streams.VideoSourceTimeline import (
    VideoSourceCandidate,
    VideoSourceTimelineResolver,
)


class VideoSourceTimelineResolverTest(unittest.TestCase):
    """部分録画ファイル群から仮想番組時間軸を構成する処理を検証する。"""

    def setUp(self) -> None:
        """各テストで共通する30分番組の EPG 時刻を初期化する。"""

        self.program_start_time = datetime(2026, 8, 12, 21, 0, tzinfo=JST)
        self.program_end_time = self.program_start_time + timedelta(minutes=30)

    def candidate(self, program_id: int, start_seconds: float, end_seconds: float) -> VideoSourceCandidate:
        """
        番組内の指定範囲を収録したテスト用候補を生成する。

        Args:
            program_id (int): 録画番組 ID。
            start_seconds (float): 番組開始から見た録画開始秒。
            end_seconds (float): 番組開始から見た録画終了秒。

        Returns:
            VideoSourceCandidate: 仮想時間軸へ渡す録画ファイル候補。
        """

        return VideoSourceCandidate(
            recorded_program_id = program_id,
            recorded_video_id = program_id + 100,
            file_path = f'/recordings/{program_id}.m2ts',
            recording_start_time = self.program_start_time + timedelta(seconds=start_seconds),
            recording_end_time = self.program_start_time + timedelta(seconds=end_seconds),
            source_duration_seconds = end_seconds - start_seconds,
            recording_start_margin = 0.0,
            recording_end_margin = 0.0,
        )

    def test_any_number_of_partial_files_can_cover_one_continuous_timeline(self) -> None:
        """3個以上の部分録画でも、重複を除いて番組全体を連続復元する。"""

        timeline = VideoSourceTimelineResolver.build(
            self.program_start_time,
            self.program_end_time,
            [
                self.candidate(1, 0, 650),
                self.candidate(2, 600, 1250),
                self.candidate(3, 1200, 1800),
            ],
        )

        self.assertTrue(timeline.is_continuous)
        self.assertEqual([span.recorded_program_id for span in timeline.spans], [1, 2, 3])
        self.assertEqual(
            [(span.timeline_start_seconds, span.timeline_end_seconds) for span in timeline.spans],
            [(0.0, 650.0), (650.0, 1250.0), (1250.0, 1800.0)],
        )
        self.assertEqual(
            [(span.source_start_seconds, span.source_end_seconds) for span in timeline.spans],
            [(0.0, 650.0), (50.0, 650.0), (50.0, 600.0)],
        )

    def test_source_covering_farthest_is_selected_for_overlap(self) -> None:
        """現在位置を覆う候補が複数ある場合、最も先まで覆えるファイルを選ぶ。"""

        timeline = VideoSourceTimelineResolver.build(
            self.program_start_time,
            self.program_end_time,
            [
                self.candidate(1, 0, 500),
                self.candidate(2, 0, 1000),
                self.candidate(3, 900, 1800),
            ],
        )

        self.assertTrue(timeline.is_continuous)
        self.assertEqual([span.recorded_program_id for span in timeline.spans], [2, 3])
        self.assertEqual(timeline.spans[1].source_start_seconds, 100.0)

    def test_real_gap_is_reported_without_compressing_timeline(self) -> None:
        """録画できていない区間は詰めず、番組時間軸上の欠落として残す。"""

        timeline = VideoSourceTimelineResolver.build(
            self.program_start_time,
            self.program_end_time,
            [self.candidate(1, 0, 500), self.candidate(2, 600, 1800)],
        )

        self.assertFalse(timeline.is_continuous)
        self.assertEqual(len(timeline.gaps), 1)
        self.assertEqual(timeline.gaps[0].timeline_start_seconds, 500.0)
        self.assertEqual(timeline.gaps[0].timeline_end_seconds, 600.0)

    def test_subsecond_boundary_rounding_is_not_treated_as_missing_content(self) -> None:
        """コンテナ時刻の1秒未満の丸め差だけは実欠落として扱わない。"""

        timeline = VideoSourceTimelineResolver.build(
            self.program_start_time,
            self.program_end_time,
            [self.candidate(1, 0, 900), self.candidate(2, 900.5, 1800)],
        )

        self.assertTrue(timeline.is_continuous)
        self.assertEqual(timeline.spans[1].timeline_start_seconds, 900.0)
        self.assertEqual(timeline.spans[1].source_start_seconds, 0.0)


if __name__ == '__main__':
    unittest.main()
